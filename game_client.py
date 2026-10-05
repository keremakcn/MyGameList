"""Credential-free game discovery with bounded caching and shared in-flight requests."""
from collections import OrderedDict
from concurrent.futures import Future
import copy
import json
import os
import re
from threading import Lock
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class GameDiscoveryError(Exception):
    def __init__(self, status=502, retry_after=3):
        super().__init__('Game discovery is temporarily unavailable.')
        self.status = status
        self.retry_after = retry_after


class GameClient:
    def __init__(self, base_url=None, capacity=256):
        base = base_url or os.environ.get('MYGAMELIST_GATEWAY_URL') or 'https://api.myshelf.cloud/rawg/'
        parts = urlsplit(base)
        if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment or parts.path.rstrip('/') != '/rawg'):
            raise ValueError('Game discovery requires an HTTPS gateway ending in /rawg/.')
        self.base_url = base.rstrip('/') + '/'
        self.capacity = capacity
        self.cache = OrderedDict()
        self.pending = {}
        self.lock = Lock()
        self.cooldown_until = 0

    def get(self, resource, **params):
        if not re.fullmatch(r'games(?:/[1-9]\d{0,9})?|developers|publishers', resource):
            raise ValueError('Unsupported game discovery resource.')
        if any(key not in {'search','page','page_size','developers','publishers','ordering','exclude_additions'} for key in params):
            raise ValueError('Unsupported discovery parameter.')
        key = (resource, urlencode(sorted(params.items())))
        with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                self.cache.move_to_end(key)
                if isinstance(cached[1], GameDiscoveryError):
                    raise cached[1]
                return copy.deepcopy(cached[1])
            if self.cooldown_until > time.monotonic():
                raise GameDiscoveryError(429, 60)
            future = self.pending.get(key)
            owner = future is None
            if owner:
                future = self.pending[key] = Future()
        if not owner:
            try:
                return copy.deepcopy(future.result(timeout=12))
            except TimeoutError:
                raise GameDiscoveryError(504) from None
        try:
            result = self._request(resource, params)
            ttl = 21600 if resource.startswith('games/') else 120
        except GameDiscoveryError as failure:
            result, ttl = failure, failure.retry_after
        except Exception:
            result, ttl = GameDiscoveryError(), 3
        with self.lock:
            self.cache[key] = (time.monotonic() + ttl, result)
            self.cache.move_to_end(key)
            while len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            self.pending.pop(key)
            if isinstance(result, GameDiscoveryError):
                if result.status == 429:
                    self.cooldown_until = time.monotonic() + result.retry_after
                future.set_exception(result)
            else:
                future.set_result(result)
        if isinstance(result, GameDiscoveryError):
            raise result
        return copy.deepcopy(result)

    def _request(self, resource, params):
        url = self.base_url + resource + ('?' + urlencode(sorted(params.items())) if params else '')
        request = Request(url, headers={'Accept':'application/json', 'User-Agent':'MyGameList/Android' if os.environ.get('MYGAMELIST_PLATFORM') == 'android' else 'MyGameList/Windows'})
        try:
            with urlopen(request, timeout=8) as response:
                raw = response.read(4*1024*1024+1)
                if len(raw) > 4*1024*1024:
                    raise GameDiscoveryError()
                data = json.loads(raw)
        except HTTPError as error:
            try:
                retry = max(1,min(120,int(error.headers.get('Retry-After','60'))))
            except (TypeError,ValueError):
                retry = 60
            raise GameDiscoveryError(error.code, retry if error.code == 429 else 3) from None
        except (URLError,OSError,ValueError):
            raise GameDiscoveryError() from None
        if not isinstance(data,dict) or data.get('success') is False:
            raise GameDiscoveryError()
        if resource.startswith('games/'):
            if data.get('id') != int(resource.split('/')[1]) or not isinstance(data.get('name'),str):
                raise GameDiscoveryError()
        elif not isinstance(data.get('results'),list):
            raise GameDiscoveryError()
        return data
