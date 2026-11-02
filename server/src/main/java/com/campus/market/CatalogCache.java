package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Component;
import redis.clients.jedis.JedisPooled;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

@Component
public class CatalogCache {
    private static final String PREFIX = "campus:cache:";
    private final int localTtlSeconds;
    private final int redisTtlSeconds;
    private final int maxItems;
    private final Map<String, Entry> local = new ConcurrentHashMap<>();
    private final ObjectMapper json = new ObjectMapper();
    private final JedisPooled redis;

    public CatalogCache(CampusProperties properties) {
        this.localTtlSeconds = properties.getCacheLocalTtlSeconds();
        this.redisTtlSeconds = properties.getCacheRedisTtlSeconds();
        this.maxItems = properties.getCacheLocalMaxItems();
        this.redis = connect(properties.getRedisUrl());
    }

    public Object read(String key, Supplier<Object> loader, HttpServletRequest request) {
        String source = "miss";
        Object value = localGet(key);
        if (value != null) {
            source = "local";
        } else {
            value = redisGet(key);
            if (value != null) {
                source = "redis";
                localSet(key, value);
            }
        }
        if (value == null) {
            value = loader.get();
            if (value == null) {
                return null;
            }
            localSet(key, value);
            redisSet(key, value);
        }
        request.setAttribute("cacheSource", source);
        return copy(value);
    }

    public void invalidate(String key) {
        local.remove(PREFIX + key);
        if (redis == null) {
            return;
        }
        try {
            redis.del(PREFIX + key);
        } catch (RuntimeException ignored) {
            // Redis 中断时不影响写入数据库。
        }
    }

    private Object localGet(String key) {
        Entry entry = local.get(PREFIX + key);
        if (entry == null || entry.expiresAt <= System.nanoTime()) {
            local.remove(PREFIX + key);
            return null;
        }
        return copy(entry.value);
    }

    private void localSet(String key, Object value) {
        if (local.size() >= maxItems) {
            local.keySet().stream().findFirst().ifPresent(local::remove);
        }
        local.put(PREFIX + key, new Entry(copy(value), System.nanoTime() + localTtlSeconds * 1_000_000_000L));
    }

    private Object redisGet(String key) {
        if (redis == null) {
            return null;
        }
        try {
            String raw = redis.get(PREFIX + key);
            return raw == null ? null : json.readValue(raw, Object.class);
        } catch (Exception ignored) {
            return null;
        }
    }

    private void redisSet(String key, Object value) {
        if (redis == null) {
            return;
        }
        try {
            redis.setex(PREFIX + key, Math.max(redisTtlSeconds, 1), json.writeValueAsString(value));
        } catch (Exception ignored) {
            // 连不上 Redis 时只保留本地缓存。
        }
    }

    private static JedisPooled connect(String redisUrl) {
        if (redisUrl == null || redisUrl.isBlank()) {
            return null;
        }
        try {
            JedisPooled client = new JedisPooled(redisUrl);
            client.ping();
            return client;
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private Object copy(Object value) {
        if (value instanceof Map<?, ?> map) {
            return new LinkedHashMap<>(map);
        }
        if (value instanceof List<?> list) {
            return new ArrayList<>(list);
        }
        return value;
    }

    private record Entry(Object value, long expiresAt) {
    }
}
