package com.campus.market;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "campus")
public class CampusProperties {
    private String dataUrl = "http://127.0.0.1:5001";
    private String jwtSecret = "dev-only-change-me-0123456789abcdef";
    private String jwtIssuer = "campus-market";
    private String jwtAudience = "campus-market-web";
    private int accessTtlSeconds = 900;
    private String frontendUrl = "http://localhost:5173";
    private String smtpHost = "";
    private int smtpPort = 1025;
    private String mailFrom = "no-reply@campus-market.local";
    private int bcryptCost = 12;
    private String phoneEncKey = "";
    private String phoneHashKey = "";
    private String redisUrl = "redis://127.0.0.1:6379/0";
    private String elasticsearchUrl = "http://127.0.0.1:9200";
    private int cacheLocalTtlSeconds = 20;
    private int cacheRedisTtlSeconds = 120;
    private int cacheLocalMaxItems = 256;

    public String getDataUrl() {
        return dataUrl;
    }

    public void setDataUrl(String dataUrl) {
        this.dataUrl = dataUrl;
    }

    public String getJwtSecret() {
        return jwtSecret;
    }

    public void setJwtSecret(String jwtSecret) {
        this.jwtSecret = jwtSecret;
    }

    public String getJwtIssuer() {
        return jwtIssuer;
    }

    public void setJwtIssuer(String jwtIssuer) {
        this.jwtIssuer = jwtIssuer;
    }

    public String getJwtAudience() {
        return jwtAudience;
    }

    public void setJwtAudience(String jwtAudience) {
        this.jwtAudience = jwtAudience;
    }

    public int getAccessTtlSeconds() {
        return accessTtlSeconds;
    }

    public void setAccessTtlSeconds(int accessTtlSeconds) {
        this.accessTtlSeconds = accessTtlSeconds;
    }

    public String getFrontendUrl() {
        return frontendUrl;
    }

    public void setFrontendUrl(String frontendUrl) {
        this.frontendUrl = frontendUrl;
    }

    public String getSmtpHost() {
        return smtpHost;
    }

    public void setSmtpHost(String smtpHost) {
        this.smtpHost = smtpHost;
    }

    public int getSmtpPort() {
        return smtpPort;
    }

    public void setSmtpPort(int smtpPort) {
        this.smtpPort = smtpPort;
    }

    public String getMailFrom() {
        return mailFrom;
    }

    public void setMailFrom(String mailFrom) {
        this.mailFrom = mailFrom;
    }

    public int getBcryptCost() {
        return bcryptCost;
    }

    public void setBcryptCost(int bcryptCost) {
        this.bcryptCost = bcryptCost;
    }

    public String getPhoneEncKey() {
        return phoneEncKey;
    }

    public void setPhoneEncKey(String phoneEncKey) {
        this.phoneEncKey = phoneEncKey;
    }

    public String getPhoneHashKey() {
        return phoneHashKey;
    }

    public void setPhoneHashKey(String phoneHashKey) {
        this.phoneHashKey = phoneHashKey;
    }

    public String getRedisUrl() {
        return redisUrl;
    }

    public void setRedisUrl(String redisUrl) {
        this.redisUrl = redisUrl;
    }

    public String getElasticsearchUrl() {
        return elasticsearchUrl;
    }

    public void setElasticsearchUrl(String elasticsearchUrl) {
        this.elasticsearchUrl = elasticsearchUrl;
    }

    public int getCacheLocalTtlSeconds() {
        return cacheLocalTtlSeconds;
    }

    public void setCacheLocalTtlSeconds(int cacheLocalTtlSeconds) {
        this.cacheLocalTtlSeconds = cacheLocalTtlSeconds;
    }

    public int getCacheRedisTtlSeconds() {
        return cacheRedisTtlSeconds;
    }

    public void setCacheRedisTtlSeconds(int cacheRedisTtlSeconds) {
        this.cacheRedisTtlSeconds = cacheRedisTtlSeconds;
    }

    public int getCacheLocalMaxItems() {
        return cacheLocalMaxItems;
    }

    public void setCacheLocalMaxItems(int cacheLocalMaxItems) {
        this.cacheLocalMaxItems = cacheLocalMaxItems;
    }
}
