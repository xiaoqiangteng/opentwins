# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

OpenTwins is a parent Helm chart (v0.6.1) for deploying an open-source digital twin IoT platform on Kubernetes. It orchestrates Eclipse Ditto, Eclipse Hono, Mosquitto, InfluxDB2, Grafana, Telegraf, MongoDB, and Kafka as sub-chart dependencies.

The repo contains multiple Helm charts — `OpenTwins/` is the main parent chart. Sibling charts (`mosquitto/`, `mqtttomongo/`, `OpenTwins-Lightweight/`, `OpenTwins-MongoDB/`) are sub-charts published independently but developed in the same repo. The root `index.yaml` in `OpenTwins/` is the Helm repo index for chart distribution via `https://ertis-research.github.io/Helm-charts/`.

Maintained by ERTIS Research Group at https://github.com/ertis-research/Helm-charts.

## Common Commands

### Installation

```bash
# Standard install/upgrade (the primary deployment command)
helm upgrade --install opentwins ./ \
  --namespace opentwins --create-namespace \
  -f values.yaml --wait --timeout 15m --dependency-update --debug

# From the published repo
helm repo add ertis https://ertis-research.github.io/Helm-charts/
helm upgrade --install opentwins ertis/OpenTwins -n opentwins --wait --dependency-update

# Update dependencies after changing requirements.yaml
helm dependency update
```

### Development

```bash
# Render templates locally (first debugging step)
helm template opentwins ./ --debug

# Validate chart
helm lint ./

# Uninstall
helm uninstall opentwins -n opentwins
```

### Operational Scripts

```bash
# Full teardown + redeploy (deletes namespace, cleans helm cache, verifies templates, deploys, validates policies)
./redeploy_steps.sh

# Post-deployment validation (pod status, services, Grafana datasources, InfluxDB buckets, Ditto policies)
./verify_deployment.sh

# Send simulated MQTT telemetry data for testing the data pipeline
python3 get_data_simulate.py
```

## Architecture

### Data Flow

```
IoT Devices → Mosquitto/Hono → Ditto (Digital Twins) → Mosquitto/Kafka → Telegraf → InfluxDB2 → Grafana
```

- **Source**: Devices send telemetry to Mosquitto (MQTT) or Hono (AMQP/HTTP)
- **Ditto ingress/egress**: Configured via `connections.ditto.source` and `connections.ditto.target` in values.yaml
- **Telegraf**: Reads from Mosquitto/Kafka, writes to InfluxDB2
- **Grafana**: Queries InfluxDB2 for dashboards, uses custom unsigned plugins (`ertis-opentwins-app`, `ertis-unity-panel`)

### Sub-chart Dependencies (requirements.yaml)

Each dependency has an `enabled` condition flag (added by OpenTwins, not part of upstream charts):

| Component | Version | Condition | Purpose |
|-----------|---------|-----------|---------|
| Eclipse Ditto | 3.3.7 | `ditto.enabled` | Digital twin management, REST API |
| MongoDB (bitnami) | ~13.18.5 | `mongodb.enabled` | Database for Ditto and Hono |
| Mosquitto | ~0.3.1 | `mosquitto.enabled` | MQTT broker |
| Telegraf | ^1.8.27 | `telegraf.enabled` | Metrics collection agent |
| InfluxDB2 | ~2.1.1 | `influxdb2.enabled` | Time-series telemetry database |
| Grafana | ~10.1.2 | `grafana.enabled` | Visualization dashboards |
| Kafka | ~22.0.0 | `kafka.enabled` | Optional message streaming |
| Eclipse Hono | ^2.5.5 | `hono.enabled` | Optional IoT device connectivity |

### Template Organization

Templates are organized by function in subdirectories:

- **`config-maps/`**: Telegraf config, Grafana datasources, plugin enabler
- **`secrets/`**: Connection credentials for Ditto, Hono, Mosquitto, MongoDB, and example devices
- **`post-install-jobs/`**: Helm hook jobs (`post-install`) that configure Ditto connections and policies after install
- **`fixers/`**: `ditto-fixer.yaml` — workaround pod for zombie connection cleanup
- **`extended-api/`**: Custom Ditto Extended API (deployment + service + nginx configmap)
- **`persistent-volumes/`**: Optional PV/PVC/StorageClass definitions (cluster-dependent, off by default)

### Post-Install Jobs

These Kubernetes Jobs use `helm.sh/hook: post-install` with retry logic:

- **`post-install-ditto-default.yaml`**: Creates Ditto policies (`default:basic_policy` and `opentwins:basic_policy`)
- **`post-install-mosquitto-source-connection.yaml`**: Mosquitto → Ditto (telemetry ingress)
- **`post-install-mosquitto-target-connection.yaml`**: Ditto → Mosquitto (twin updates egress)
- **`post-install-hono-source-connection.yaml`**: Hono → Ditto (optional)
- **`post-install-example-raspberry.yaml`**: Example Raspberry Pi digital twin

Policies are created via post-install jobs, NOT via Ditto's bootstrap mechanism. The bootstrap approach fails because Ditto chart v3.3.7 overrides `JAVA_TOOL_OPTIONS`, ignoring custom `-Dditto.bootstrap.policies.file`.

Policy JSON files and setup scripts live in `post-install/ditto-default/`, `post-install/ditto-mosquitto-connection/`, etc.

### Ditto Fixer

`templates/fixers/ditto-fixer.yaml` deploys a monitoring pod that snapshots open Ditto connections to a PVC, detects crashes, and restarts zombie connections. Enabled via `ditto.cleanupStaleConnections: true`. Addresses a known Ditto issue where connections stay in a zombie state after crashes.

### Extended API

`templates/extended-api/` defines a custom Ditto Extended API service with its own nginx reverse proxy, exposed via NodePort 30526.

## Key Values Patterns

### Container Image Registry

All images use the Aliyun registry `crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/*`. Each sub-chart uses a different image field convention — check the upstream chart's values.yaml:

- **Grafana**: separate `registry` + `repository` fields
- **Telegraf**: `repo` (not `repository`)
- **Ditto components**: full path in `repository`
- **Ditto nginx initContainers**: plain image string, not object format

Never set `registry: ""` — it causes malformed image paths. See `ALIYUN_REGISTRY_FIX.md` for details.

### Connection Configuration

```yaml
connections:
  ditto:
    source:        # Where Ditto receives telemetry
      hono: {...}
      mosquitto: {...}
    target:        # Where Ditto publishes twin updates
      mosquitto: {...}
      kafka: {...}
  telegraf:
    source:        # Where Telegraf subscribes
      mosquitto: {...}
    target:        # Where Telegraf writes metrics
      influxdb2: {...}
```

### External Resources

- `externalInfluxdb2`: List of external InfluxDB instances auto-connected to Grafana/Telegraf
- `externalMosquitto`: List of external MQTT brokers auto-connected to Ditto

### Important Defaults

- `DITTO_POLICIES_ENFORCE: "false"` — policies not enforced by default
- MongoDB authentication disabled by default
- InfluxDB2 admin token is pre-generated in values.yaml (change in production)
- Grafana credentials: `admin` / `Test123456!`
- Ditto credentials: `ditto:ditto` (user), `devops:foobar` (devops)

## Template Helpers

Defined in `templates/_helpers.tpl`:

- `opentwins.{component}.fullname` — generates DNS-compliant full names for sub-chart resources (e.g., `opentwins.ditto.fullname` resolves to `opentwins-ditto`)
- `installation.name` — returns `.Release.Name`
- `opentwins.labels`, `opentwins.selectorLabels` — standard Helm label sets
- `opentwins.extendedAPI.fullname` — generates the Extended API deployment name

The `nameOverride` values (e.g., `ditto.nameOverride: ditto`, `mongodb.nameOverride: mongodb`) are critical — they determine service DNS names used in cross-component connection configs.

## Debugging

```bash
# Render templates locally first
helm template opentwins ./ --debug

# Check post-install job logs
kubectl logs -n opentwins job/opentwins-post-install-ditto-default

# Verify Ditto connections
kubectl exec -it -n opentwins deployment/opentwins-ditto-gateway -- \
  curl -u devops:foobar http://localhost:8080/api/2/connections

# Check ditto-fixer logs
kubectl logs -n opentwins deployment/opentwins-ditto-fixer -f

# Verify policies were created
kubectl exec -n opentwins deployment/opentwins-ditto-gateway -- \
  curl -s -u ditto:ditto http://opentwins-ditto-nginx:8080/api/2/policies/opentwins:basic_policy | jq .
```

### Common Issues

- **Post-install job image format**: Ditto post-install jobs must use plain `image: <registry>/<image>:<tag>` strings, not structured `{repository, tag}` objects
- **Persistent volumes**: `persistentVolumes` flags depend on cluster auto-provisioning behavior
- **Zombie connections**: Enable `ditto.cleanupStaleConnections` if connections don't recover after crashes
- **Image pull errors**: Aliyun registry may require docker login credentials in the cluster
