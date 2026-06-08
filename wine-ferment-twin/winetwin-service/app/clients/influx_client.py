import csv
import io
import time
import requests

# 连通性缓存：记录上次连接失败的时间，短时间内不再重试
_failure_cache: dict[str, float] = {}
_RETRY_INTERVAL = 60.0  # 失败后 60 秒内不再重试


def _is_recently_failed(key: str) -> bool:
    t = _failure_cache.get(key)
    if t is None:
        return False
    return (time.monotonic() - t) < _RETRY_INTERVAL


def _mark_failed(key: str):
    _failure_cache[key] = time.monotonic()


def _mark_ok(key: str):
    _failure_cache.pop(key, None)


class InfluxClient:
    def __init__(self, url, token, org, bucket):
        self.url = url.rstrip('/')
        self.token = token
        self.org = org
        self.bucket = bucket
        self._cache_key = f"influx:{self.url}"

    def query_metric(self, tank_id, metric, hours=48, start_time=None):
        if not self.token:
            return []

        # 如果最近刚失败过，直接跳过
        if _is_recently_failed(self._cache_key):
            return []

        field = f"value_{metric}_properties_value"

        # 如果有 start_time，使用它作为查询起始点（当前轮次边界）
        if start_time:
            if isinstance(start_time, str):
                start = start_time
            else:
                start = start_time.isoformat()
            range_clause = f'|> range(start: {start})'
        else:
            range_clause = f'|> range(start: -{int(hours)}h)'

        flux = f'''from(bucket: "{self.bucket}")
  {range_clause}
  |> filter(fn: (r) => r._measurement == "mqtt_consumer")
  |> filter(fn: (r) => r.thingId == "wine:{tank_id}")
  |> filter(fn: (r) => r._field == "{field}")
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
'''
        try:
            response = requests.post(
                self.url + '/api/v2/query',
                params={'org': self.org},
                headers={
                    'Authorization': 'Token ' + self.token,
                    'Accept': 'application/csv',
                    'Content-type': 'application/vnd.flux',
                },
                data=flux,
                timeout=(1, 2),
            )
            _mark_ok(self._cache_key)
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
        except Exception as e:
            _mark_failed(self._cache_key)
            print('influx query failed', e)
            return []
