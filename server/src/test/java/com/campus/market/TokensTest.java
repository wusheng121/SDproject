package com.campus.market;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;

class TokensTest {
    @Test
    void accessTokenUsesHs256ForPythonCompatibility() {
        CampusProperties properties = new CampusProperties();
        properties.setJwtSecret("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
        properties.setAccessTtlSeconds(900);

        Tokens tokens = new Tokens(properties);
        String token = tokens.accessToken(2, "admin");
        String header = new String(
                Base64.getUrlDecoder().decode(token.split("\\.")[0]),
                StandardCharsets.UTF_8
        );

        assertTrue(header.contains("\"alg\":\"HS256\""), header);

        String payload = new String(
                Base64.getUrlDecoder().decode(token.split("\\.")[1]),
                StandardCharsets.UTF_8
        );
        assertTrue(payload.contains("\"roles\":[]"), payload);
        assertTrue(payload.contains("\"permissions\":[]"), payload);
    }

    @Test
    void tokenCarriesRoleAndPermissionUnion() {
        CampusProperties properties = new CampusProperties();
        properties.setJwtSecret("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
        Tokens tokens = new Tokens(properties);
        String token = tokens.accessToken(
                2,
                "admin",
                List.of("normal_user", "admin"),
                List.of("product:audit", "user:manage")
        );
        String payload = new String(
                Base64.getUrlDecoder().decode(token.split("\\.")[1]),
                StandardCharsets.UTF_8
        );
        assertTrue(payload.contains("normal_user"), payload);
        assertTrue(payload.contains("product:audit"), payload);
    }
}
