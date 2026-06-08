from urllib.parse import quote
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


class DittoClient:
    def __init__(self, base_url, username='ditto', password='ditto'):
        self.base = base_url.rstrip('/')
        self.auth = (username, password)
        self._cache_key = f"ditto:{self.base}"

    def get_thing(self, thing_id):
        # 如果最近刚失败过，直接跳过
        if _is_recently_failed(self._cache_key):
            raise ConnectionError(f"Ditto recently unreachable: {self.base}")
        try:
            r = requests.get(
                self.base + '/api/2/things/' + quote(thing_id, safe=''),
                auth=self.auth,
                timeout=(1, 2),
            )
            _mark_ok(self._cache_key)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            _mark_failed(self._cache_key)
            raise e

    def list_things(self, ids):
        out = []
        for i in ids:
            try:
                d = self.get_thing(i)
                if d:
                    out.append(d)
            except Exception as e:
                print('ditto read failed', i, e)
        return out
