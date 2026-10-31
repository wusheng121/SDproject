"""两级缓存。

读的时候先查本进程里的本地缓存，没有再查 Redis。两边都没有才读数据库，
然后同时写回本地和 Redis。本地缓存只在当前进程有效，过期更短；
Redis 给多个进程共用。改商品状态或产生成交时，写请求会删掉这两边的键。
别的进程里还留着的本地副本，等到较短的本地过期时间结束才会重新向 Redis 要。
Redis 连不上时只使用本地缓存，读请求仍然成功。
"""

import json
import logging
import time
from collections import OrderedDict
from threading import Lock

from flask import current_app, g

logger = logging.getLogger(__name__)

PREFIX = "campus:cache:"


class LocalCache:
    """进程内缓存。最近使用的留在末尾，超过容量就删掉最久没用的。"""

    def __init__(self, max_items: int):
        self.max_items = max_items
        self._items = OrderedDict()
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value, ttl: int) -> None:
        with self._lock:
            self._items[key] = (value, time.monotonic() + ttl)
            self._items.move_to_end(key)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class RedisCache:
    def __init__(self, client):
        self.client = client

    def get(self, key: str):
        raw = self.client.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)

    def set(self, key: str, value, ttl: int) -> None:
        self.client.set(key, json.dumps(value, ensure_ascii=False), ex=max(int(ttl), 1))

    def delete(self, key: str) -> None:
        self.client.delete(key)


class TwoLevelCache:
    def __init__(self, local: LocalCache, remote: RedisCache | None, local_ttl: int, remote_ttl: int):
        self.local = local
        self.remote = remote
        self.local_ttl = local_ttl
        self.remote_ttl = remote_ttl
        self._known = set()

    def get(self, key: str):
        full = PREFIX + key
        local_value = self.local.get(full)
        if local_value is not None:
            return _copy(local_value), "local"
        if self.remote is not None:
            try:
                remote_value = self.remote.get(full)
            except Exception:
                logger.warning("读取 Redis 缓存失败", exc_info=True)
                remote_value = None
            if remote_value is not None:
                self.local.set(full, remote_value, self.local_ttl)
                return _copy(remote_value), "redis"
        return None, "miss"

    def set(self, key: str, value) -> None:
        full = PREFIX + key
        stored = json.loads(json.dumps(value, ensure_ascii=False))
        self.local.set(full, stored, self.local_ttl)
        self._known.add(full)
        if self.remote is None:
            return
        try:
            self.remote.set(full, stored, self.remote_ttl)
        except Exception:
            logger.warning("写入 Redis 缓存失败", exc_info=True)

    def invalidate(self, key: str) -> None:
        full = PREFIX + key
        self.local.delete(full)
        self._known.discard(full)
        if self.remote is None:
            return
        try:
            self.remote.delete(full)
        except Exception:
            logger.warning("删除 Redis 缓存失败", exc_info=True)

    def clear(self) -> None:
        self.local.clear()
        keys = list(self._known)
        self._known.clear()
        if self.remote is None:
            return
        for key in keys:
            try:
                self.remote.delete(key)
            except Exception:
                logger.warning("清空 Redis 缓存失败", exc_info=True)
                return


def _copy(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


def build_cache(redis_url: str, local_ttl: int, remote_ttl: int, max_items: int) -> TwoLevelCache:
    local = LocalCache(max_items)
    remote = None
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(
                redis_url,
                socket_connect_timeout=0.3,
                socket_timeout=0.3,
                decode_responses=True,
            )
            client.ping()
            remote = RedisCache(client)
            logger.info("商品缓存已连接 Redis")
        except Exception:
            logger.warning("Redis 不可用，商品缓存只保留在本进程")
    return TwoLevelCache(local, remote, local_ttl, remote_ttl)


def read_through(key: str, loader):
    """返回缓存值。未命中时调用 loader；loader 返回 None 表示不缓存。"""
    cache: TwoLevelCache = current_app.extensions["catalog_cache"]
    value, source = cache.get(key)
    if source == "miss":
        value = loader()
        if value is None:
            return None
        cache.set(key, value)
    g.cache_source = source
    return value


def invalidate_product(product_id: int, category_names=()) -> None:
    cache = current_app.extensions.get("catalog_cache")
    if cache is None:
        return
    cache.invalidate(f"product:{product_id}")
    for name in category_names:
        if name:
            cache.invalidate(f"price:{name}")
