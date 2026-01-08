# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

OpenTwins is a Helm chart for deploying an open-source digital twin IoT platform on Kubernetes. It orchestrates multiple components including Eclipse Ditto, Eclipse Hono, Mosquitto, InfluxDB2, Grafana, Telegraf, MongoDB, and Kafka.

**Current Version**: 0.6.1
**App Version**: 0.5.0

## Common Commands

### Installation and Testing

```bash
# Local testing with dependencies
helm install opentwins ./ --wait --timeout=15m --dependency-update --debug

# Standard installation from repository
helm upgrade --install opentwins ertis/OpenTwins -n opentwins --wait --dependency-update

# Update dependencies
helm dependency update

# Render templates locally (useful for debugging)
helm template opentwins ./ --debug

# Validate chart
helm lint ./
```

### Development Workflow

```bash
# Add the ERTIS helm repository
helm repo add ertis https://ertis-research.github.io/Helm-charts/
helm repo update

# Uninstall release
helm uninstall opentwins -n opentwins

# Get release status
helm status opentwins -n opentwins

# List all resources
kubectl get all -n opentwins
```

## Architecture

### Component Hierarchy

OpenTwins is a **parent Helm chart** that manages multiple sub-charts as dependencies (defined in `requirements.yaml`):

1. **Eclipse Ditto** (v3.3.7) - Digital twin management and REST API
2. **MongoDB** (bitnami v13.18.5) - Database for Ditto and Hono device registry
3. **Mosquitto** (v0.3.1) - MQTT message broker
4. **Telegraf** (v1.8.27) - Metrics collection agent
5. **InfluxDB2** (v2.1.1) - Time-series database for telemetry
6. **Grafana** (v10.1.2) - Visualization and monitoring
7. **Kafka** (v22.0.0) - Optional message streaming platform
8. **Eclipse Hono** (v2.5.5) - Optional IoT device connectivity

### Data Flow Architecture

```
IoT Devices → Mosquitto/Hono → Ditto (Digital Twins) → Mosquitto/Kafka → Telegraf → InfluxDB2 → Grafana
```

**Key data paths:**
- **Source connections**: IoT devices send telemetry to Mosquitto (MQTT) or Hono (AMQP/HTTP)
- **Ditto ingress**: Ditto consumes messages from source brokers (values: `connections.ditto.source`)
- **Ditto egress**: Ditto publishes twin updates to target brokers (values: `connections.ditto.target`)
- **Database storage**: Telegraf reads from Mosquitto/Kafka and writes to InfluxDB2
- **Visualization**: Grafana queries InfluxDB2 for dashboards

### Template Organization

Templates are organized by function in subdirectories:

- **`config-maps/`**: Dynamic configuration for Telegraf, Grafana datasources, and plugins
- **`secrets/`**: Connection credentials for Ditto, Hono, Mosquitto, MongoDB, and example devices
- **`post-install-jobs/`**: Kubernetes Jobs that run after installation to establish connections between components
- **`fixers/`**: Workaround deployments (e.g., ditto-fixer for zombie connection cleanup)
- **`extended-api/`**: Custom Ditto Extended API deployment and service
- **`persistent-volumes/`**: Optional PV/PVC/StorageClass definitions (cluster-dependent)

### Critical Post-Install Jobs

Post-install jobs use Helm hooks (`helm.sh/hook: post-install`) to automatically configure connections:

- **`post-install-ditto-default.yaml`**: Creates default Ditto policies (`default:basic_policy` and `opentwins:basic_policy`)
- **`post-install-mosquitto-source-connection.yaml`**: Connects Mosquitto → Ditto (telemetry ingress)
- **`post-install-mosquitto-target-connection.yaml`**: Connects Ditto → Mosquitto (twin updates egress)
- **`post-install-hono-source-connection.yaml`**: Optional Hono → Ditto connection
- **`post-install-example-raspberry.yaml`**: Creates example Raspberry Pi digital twin

These jobs use retry logic and environment variables for reliability (see git commit db0676f).

**Important**: Policies are created via post-install jobs, NOT via Ditto's bootstrap mechanism. The bootstrap approach doesn't work with Ditto chart v3.3.7 because the subchart overrides environment variables.

### Ditto Fixer Deployment

The `ditto-fixer.yaml` implements a persistent monitoring pod that:
1. Periodically snapshots open Ditto connections to a PVC
2. Detects system crashes via health checks
3. Automatically restarts zombie connections after recovery
4. Enabled via `ditto.cleanupStaleConnections: true`

This addresses a known issue where Ditto connections remain in a "zombie" state (neither open nor closed) after crashes.

## Values Structure

The `values.yaml` file is heavily customized with OpenTwins-specific configuration:

### Component Enablement
Each major component has an `enabled` flag (e.g., `ditto.enabled`, `mosquitto.enabled`, `hono.enabled`). This pattern was added by OpenTwins and is not part of the upstream charts.

### Connection Configuration
The `connections` section orchestrates inter-component communication:

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

### External Resource Integration
- `externalInfluxdb2`: List of external InfluxDB instances to connect to Grafana/Telegraf
- `externalMosquitto`: List of external MQTT brokers to connect to Ditto

### Custom Images
Most components use custom container registry: `crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/*`

### Important Defaults
- Ditto policies enforcement is **disabled** by default (`DITTO_POLICIES_ENFORCE: "false"`)
- MongoDB authentication is **disabled** by default
- Grafana uses unsigned custom plugins: `ertis-opentwins-app`, `ertis-unity-panel`
- InfluxDB2 token is pre-generated (should be changed in production)

## Template Helper Functions

Key helpers in `templates/_helpers.tpl`:

- `opentwins.{component}.fullname`: Generates full resource names for sub-charts (e.g., `opentwins.ditto.fullname`)
- `installation.name`: Returns the Helm release name
- Standard Helm helpers: `opentwins.name`, `opentwins.chart`, `opentwins.labels`

These are critical for cross-referencing resources between the parent chart and sub-charts.

## Testing and Debugging

### Debugging Template Issues
1. Use `helm template` to render templates locally before installation
2. Check sub-chart values are passed correctly using `{{- toYaml .Values.ditto | nindent 2 }}`
3. Verify `nameOverride` settings match expected service DNS names

### Common Issues
- **Persistent volumes**: `persistentVolumes` flags depend on cluster auto-provisioning behavior
- **Post-install job failures**: Jobs have retry logic but may fail if components aren't ready
- **Zombie connections**: Enable `ditto.cleanupStaleConnections` if Ditto connections don't recover after crashes
- **Image pull errors**: Custom registry may require authentication

### Inspecting Running Installation
```bash
# Check post-install job logs
kubectl logs -n opentwins job/opentwins-post-install-ditto-default

# Check ditto-fixer logs
kubectl logs -n opentwins deployment/opentwins-ditto-fixer -f

# Verify Ditto connections
kubectl exec -it -n opentwins deployment/opentwins-ditto-gateway -- curl -u devops:foobar http://localhost:8080/api/2/connections
```

## Policy Configuration

Ditto policies are **automatically created via post-install job**, not via bootstrap file mounting.

**Why not bootstrap?**
- The `values.yaml` previously had bootstrap configuration (`policies.env`, `extraVolumes`), but it doesn't work
- Ditto chart v3.3.7 overrides `JAVA_TOOL_OPTIONS` with default values, ignoring custom `-Dditto.bootstrap.policies.file`
- `extraVolumes` and `extraVolumeMounts` are not applied to the policies deployment

**Current implementation (post-install job):**
- Policy JSON files: `post-install/ditto-default/basic-policy.json` and `opentwins-policy.json`
- Setup script: `post-install/ditto-default/setup.sh`
- Secret template: `templates/secrets/ditto-default-secret.yaml` (embeds JSON files)
- Job template: `templates/post-install-jobs/post-install-ditto-default.yaml`

**Created policies:**
1. `default:basic_policy` - For default Ditto resources
2. `opentwins:basic_policy` - For OpenTwins platform resources (includes `nginx:ditto` subject)

Both policies grant READ/WRITE access to `policy:/`, `thing:/`, and `message:/` resources.

## Maintenance Notes

- Bitnami images use `bitnamilegacy` repository for older versions (see git commit b11cca0)
- Grafana upgraded to v12.3 with OpenTwins auto-config (git commit b7cd03a)
- Correlation IDs can now be stored in InfluxDB (git commit 36e7a54)
- The repository is maintained by ERTIS Research Group at https://github.com/ertis-research/Helm-charts

## Container Image Registry Configuration

All container images are configured to use Aliyun (Alibaba Cloud) registry for better availability in China.

### Key Configuration Principles

1. **Grafana Images**: Use separate `registry` and `repository` fields
   ```yaml
   grafana:
     image:
       registry: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com
       repository: opentwins/grafana
   ```

2. **Telegraf Images**: Use `repo` instead of `repository`
   ```yaml
   telegraf:
     image:
       repo: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/telegraf
   ```

3. **Other Images**: Use full path in `repository` field
   ```yaml
   ditto:
     gateway:
       image:
         repository: crpi-ur4vz1dcuzowzd01.cn-beijing.personal.cr.aliyuncs.com/opentwins/ditto-gateway
   ```

### Common Issues

- **Empty registry causes "/path" format error**: Never set `registry: ""`, either omit it or set proper value
- **Chart-specific field names**: Check each subchart's values.yaml for correct field names (`repo` vs `repository`)
- **Init container format**: Ditto nginx initContainers expect plain image string, not object format

See `ALIYUN_REGISTRY_FIX.md` for complete image configuration documentation.

