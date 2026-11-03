package com.campus.market;

import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class IntentClient {
    private final RestClient client;
    private final CampusProperties properties;

    public IntentClient(CampusProperties properties) {
        this.properties = properties;
        String root = properties.getDataUrl();
        if (root.endsWith("/")) {
            root = root.substring(0, root.length() - 1);
        }
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);
        factory.setReadTimeout(8000);
        this.client = RestClient.builder().baseUrl(root).requestFactory(factory).build();
    }

    public Map<String, Object> classify(String message, Map<String, Object> fallback) {
        try {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("message", message);
            Map<?, ?> response = client.post()
                    .uri("/api/ai/intent")
                    .header("X-Internal-Token", properties.getJwtSecret())
                    .body(body)
                    .retrieve()
                    .body(Map.class);
            Object data = response == null ? null : response.get("data");
            if (data instanceof Map<?, ?> map) {
                Map<String, Object> result = new LinkedHashMap<>();
                map.forEach((key, value) -> result.put(String.valueOf(key), value));
                if (result.get("intent") != null && result.get("sub_agent") != null) {
                    return result;
                }
            }
        } catch (Exception ignored) {
            // Python 数据服务不可用时回到规则路由。
        }
        return fallback;
    }
}
