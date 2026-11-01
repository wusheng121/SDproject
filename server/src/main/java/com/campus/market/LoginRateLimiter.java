package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class LoginRateLimiter {
    private static final int LIMIT = 15;
    private static final long WINDOW_SECONDS = 60;
    private final Map<String, Deque<Instant>> hits = new ConcurrentHashMap<>();

    public void hit(HttpServletRequest request, String action) {
        String forwarded = request.getHeader("X-Forwarded-For");
        String ip = forwarded == null || forwarded.isBlank() ? request.getRemoteAddr() : forwarded.split(",")[0].trim();
        String key = action + ":" + (ip == null ? "" : ip);
        Instant now = Instant.now();
        Deque<Instant> recent = hits.computeIfAbsent(key, ignored -> new ArrayDeque<>());
        synchronized (recent) {
            while (!recent.isEmpty() && recent.peekFirst().isBefore(now.minusSeconds(WINDOW_SECONDS))) {
                recent.removeFirst();
            }
            if (recent.size() >= LIMIT) {
                throw new ApiException("RATE_LIMIT", "操作太频繁，请一分钟后再试", 429);
            }
            recent.addLast(now);
        }
    }
}
