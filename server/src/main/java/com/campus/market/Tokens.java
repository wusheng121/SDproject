package com.campus.market;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.HexFormat;
import java.util.List;

@Component
public class Tokens {
    private final CampusProperties properties;
    private final BCryptPasswordEncoder passwords;

    public Tokens(CampusProperties properties) {
        this.properties = properties;
        int cost = properties.getBcryptCost();
        this.passwords = new BCryptPasswordEncoder(cost < 4 || cost > 31 ? 12 : cost);
    }

    public boolean passwordMatches(String raw, String hash) {
        if (raw == null || hash == null || hash.isBlank()) {
            return false;
        }
        return passwords.matches(raw, hash);
    }

    public String hashPassword(String raw) {
        return passwords.encode(raw);
    }

    public String accessToken(long userId, String userType) {
        return accessToken(userId, userType, List.of(), List.of());
    }

    public String accessToken(long userId, String userType, List<String> roles, List<String> permissions) {
        Instant now = Instant.now();
        SecretKey key = Keys.hmacShaKeyFor(pad(properties.getJwtSecret()));
        return Jwts.builder()
                .header().add("kid", "v1").and()
                .subject(Long.toString(userId))
                .claim("type", "access")
                .claim("user_type", userType)
                .claim("roles", roles)
                .claim("permissions", permissions)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(properties.getAccessTtlSeconds())))
                .issuer(properties.getJwtIssuer())
                .audience().add(properties.getJwtAudience()).and()
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    public Long userId(HttpServletRequest request) {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return null;
        }
        String token = header.substring(7).trim();
        try {
            SecretKey key = Keys.hmacShaKeyFor(pad(properties.getJwtSecret()));
            var claims = Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
            if (!"access".equals(claims.get("type"))) {
                return null;
            }
            return Long.parseLong(claims.getSubject());
        } catch (RuntimeException exc) {
            return null;
        }
    }

    public String userType(HttpServletRequest request) {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return "";
        }
        try {
            SecretKey key = Keys.hmacShaKeyFor(pad(properties.getJwtSecret()));
            var claims = Jwts.parser().verifyWith(key).build().parseSignedClaims(header.substring(7).trim()).getPayload();
            Object role = claims.get("user_type");
            return role == null ? "" : String.valueOf(role);
        } catch (RuntimeException exc) {
            return "";
        }
    }

    public static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (Exception exc) {
            throw new IllegalStateException(exc);
        }
    }

    public static String refreshCookie(String raw) {
        return ResponseCookie.from("cm_refresh", raw)
                .httpOnly(true)
                .path("/api/v1/auth")
                .sameSite("Lax")
                .maxAge(Duration.ofDays(30))
                .build()
                .toString();
    }

    public static String clearRefreshCookie() {
        return ResponseCookie.from("cm_refresh", "")
                .httpOnly(true)
                .path("/api/v1/auth")
                .maxAge(0)
                .build()
                .toString();
    }

    public static String readCookie(HttpServletRequest request, String name) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        for (Cookie cookie : cookies) {
            if (name.equals(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return null;
    }

    private static byte[] pad(String secret) {
        byte[] raw = secret.getBytes(StandardCharsets.UTF_8);
        if (raw.length >= 32) {
            return raw;
        }
        byte[] padded = new byte[32];
        System.arraycopy(raw, 0, padded, 0, raw.length);
        return padded;
    }
}
