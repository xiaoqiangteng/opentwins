import csv
import io
import requests


class InfluxClient:
    def __init__(self, url, token, org, bucket):
        self.url = url.rstrip('/')
        self.token = token
        self.org = org
        self.bucket = bucket

    def query_metric(self, tank_id, metric, hours=48):
        if not self.token:
            return []
        field = f"value_{metric}_properties_value"
        flux = f'''from(bucket: "{self.bucket}")
  |> range(start: -{int(hours)}h)
  |> filter(fn: (r) => r._measurement == "mqtt_consumer")
  |> filter(fn: (r) => r.thingId == "wine:{tank_id}")
  |> filter(fn: (r) => r._field == "{field}")
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
'''
        response = requests.post(
            self.url + '/api/v2/query',
            params={'org': self.org},
            headers={
                'Authorization': 'Token ' + self.token,
                'Accept': 'application/csv',
                'Content-type': 'application/vnd.flux',
            },
            data=flux,
            timeout=8,
        )
        if response.status_code >= 400:
            print('influx query failed', response.status_code, response.text[:200])
            return []
        points = []
        reader = csv.DictReader(line for line in io.StringIO(response.text) if line and not line.startswith('#'))
        for row in reader:
            try:
                timestamp = row.get('_time')
                value = row.get('_value')
                if timestamp is not None and value not in (None, ''):
                    points.append({'timestamp': timestamp, 'value': float(value)})
            except Exception:
                continue
        return points
