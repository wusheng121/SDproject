package com.campus.market;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class BackendEnv {
    private static final Pattern MYSQL = Pattern.compile(
            "mysql\\+pymysql://([^:]+):([^@]+)@([^:/]+):(\\d+)/([^?]+)"
    );

    private BackendEnv() {
    }

    public static void load() {
        Map<String, String> values = readFile();
        put("SECRET_KEY", values);
        put("JWT_ISSUER", values);
        put("JWT_AUDIENCE", values);
        put("JWT_ACCESS_TTL_SECONDS", values);
        put("BCRYPT_COST", values);
        put("PHONE_ENC_KEY", values);
        put("PHONE_HASH_KEY", values);
        put("FRONTEND_URL", values);
        put("SMTP_HOST", values);
        put("SMTP_PORT", values);
        put("MAIL_FROM", values);
        put("REDIS_URL", values);
        put("RABBITMQ_HOST", values);
        put("RABBITMQ_PORT", values);
        put("RABBITMQ_USER", values);
        put("RABBITMQ_PASSWORD", values);
        put("ELASTICSEARCH_URL", values);
        put("CACHE_LOCAL_TTL_SECONDS", values);
        put("CACHE_REDIS_TTL_SECONDS", values);
        put("CACHE_LOCAL_MAX_ITEMS", values);
        applyDatabase(values.get("DATABASE_URL"));
    }

    private static Map<String, String> readFile() {
        Path path = Path.of("..", "backend", ".env");
        if (!Files.exists(path)) {
            path = Path.of("backend", ".env");
        }
        Map<String, String> values = new LinkedHashMap<>();
        if (!Files.exists(path)) {
            return values;
        }
        try {
            for (String line : Files.readAllLines(path)) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#") || !trimmed.contains("=")) {
                    continue;
                }
                int split = trimmed.indexOf('=');
                values.put(trimmed.substring(0, split).trim(), trimmed.substring(split + 1).trim());
            }
        } catch (Exception ignored) {
            return values;
        }
        return values;
    }

    private static void put(String name, Map<String, String> values) {
        if (System.getenv(name) != null || System.getProperty(name) != null) {
            return;
        }
        if (values.containsKey(name)) {
            System.setProperty(name, values.get(name));
        }
    }

    private static void applyDatabase(String databaseUrl) {
        if (databaseUrl == null || System.getProperty("spring.datasource.url") != null) {
            return;
        }
        Matcher matcher = MYSQL.matcher(databaseUrl);
        if (!matcher.find()) {
            return;
        }
        System.setProperty("spring.datasource.username", matcher.group(1));
        System.setProperty("spring.datasource.password", matcher.group(2));
        System.setProperty(
                "spring.datasource.url",
                "jdbc:mysql://" + matcher.group(3) + ":" + matcher.group(4) + "/" + matcher.group(5)
                        + "?characterEncoding=UTF-8&serverTimezone=UTC"
        );
    }
}
