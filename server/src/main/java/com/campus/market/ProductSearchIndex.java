package com.campus.market;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.http.HttpHost;
import org.elasticsearch.client.Request;
import org.elasticsearch.client.Response;
import org.elasticsearch.client.RestClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class ProductSearchIndex {
    private static final Logger log = LoggerFactory.getLogger(ProductSearchIndex.class);
    private static final String INDEX = "campus-products";
    private final String url;
    private final MarketStore store;
    private final ObjectMapper json = new ObjectMapper();
    private volatile RestClient client;
    private volatile long unavailableUntil;

    @Autowired
    public ProductSearchIndex(CampusProperties properties, MarketStore store) {
        this(properties.getElasticsearchUrl(), store);
    }

    ProductSearchIndex(String url, MarketStore store) {
        this.url = url == null ? "" : url.trim();
        this.store = store;
    }

    public List<Long> findIds(String keyword) {
        if (url.isBlank() || keyword == null || keyword.isBlank() || System.currentTimeMillis() < unavailableUntil) {
            return null;
        }
        try {
            Map<String, Object> body = Map.of(
                    "size", 50,
                    "query", Map.of("bool", Map.of(
                            "must", List.of(Map.of("multi_match", Map.of(
                                    "query", keyword,
                                    "fields", List.of("name^3", "categories^2", "description")))),
                            "filter", List.of(Map.of("term", Map.of("status", "approved"))))));
            JsonNode hits = perform("POST", "/" + INDEX + "/_search", body).path("hits").path("hits");
            List<Long> ids = new ArrayList<>();
            if (hits.isArray()) {
                for (JsonNode hit : hits) {
                    ids.add(Long.parseLong(hit.path("_id").asText()));
                }
            }
            return ids;
        } catch (Exception exc) {
            markDown("关键词搜索");
            return null;
        }
    }

    public void sync(long productId) {
        if (url.isBlank() || store == null || System.currentTimeMillis() < unavailableUntil) {
            return;
        }
        try {
            Map<String, Object> product = store.product(productId);
            if (product == null || !"approved".equals(String.valueOf(product.get("status")))) {
                Request request = new Request("DELETE", "/" + INDEX + "/_doc/" + productId);
                client().performRequest(request);
                return;
            }
            perform("PUT", "/" + INDEX + "/_doc/" + productId, document(product));
        } catch (org.elasticsearch.client.ResponseException exc) {
            if (exc.getResponse().getStatusLine().getStatusCode() != 404) {
                markDown("同步商品 " + productId);
            }
        } catch (Exception exc) {
            markDown("同步商品 " + productId);
        }
    }

    @EventListener(ApplicationReadyEvent.class)
    public void rebuildWhenReady() {
        Thread worker = new Thread(this::rebuild, "product-index");
        worker.setDaemon(true);
        worker.start();
    }

    void rebuild() {
        if (url.isBlank() || store == null) {
            return;
        }
        try {
            unavailableUntil = 0;
            ensureIndex();
            StringBuilder bulk = new StringBuilder();
            int count = 0;
            for (Map<String, Object> product : store.allProducts()) {
                long id = MarketStore.num(product.get("id"));
                if (!"approved".equals(String.valueOf(product.get("status")))) {
                    bulk.append("{\"delete\":{\"_index\":\"").append(INDEX).append("\",\"_id\":\"").append(id).append("\"}}\n");
                } else {
                    bulk.append("{\"index\":{\"_index\":\"").append(INDEX).append("\",\"_id\":\"").append(id).append("\"}}\n");
                    bulk.append(json.writeValueAsString(document(product))).append('\n');
                    count++;
                }
            }
            if (!bulk.isEmpty()) {
                Request request = new Request("POST", "/_bulk");
                request.setJsonEntity(bulk.toString());
                client().performRequest(request);
            }
            log.info("站内搜索已写入 Elasticsearch，在售商品 {} 件", count);
        } catch (Exception exc) {
            markDown("重建索引");
        }
    }

    private void ensureIndex() throws Exception {
        Request head = new Request("HEAD", "/" + INDEX);
        try {
            Response response = client().performRequest(head);
            if (response.getStatusLine().getStatusCode() == 200) {
                return;
            }
        } catch (org.elasticsearch.client.ResponseException exc) {
            if (exc.getResponse().getStatusLine().getStatusCode() != 404) {
                throw exc;
            }
        }
        Map<String, Object> text = Map.of("type", "text", "analyzer", "cjk");
        perform("PUT", "/" + INDEX, Map.of(
                "settings", Map.of("number_of_shards", 1, "number_of_replicas", 0),
                "mappings", Map.of("properties", Map.of(
                        "name", text,
                        "description", text,
                        "categories", text,
                        "status", Map.of("type", "keyword")))));
    }

    private Map<String, Object> document(Map<String, Object> product) {
        long id = MarketStore.num(product.get("id"));
        Map<String, Object> document = new LinkedHashMap<>();
        document.put("name", MarketStore.str(product.get("name")));
        document.put("description", MarketStore.str(product.get("description")));
        document.put("categories", String.join(" ", store.categoriesOf(id)));
        document.put("status", MarketStore.str(product.get("status")));
        document.put("price", product.get("price"));
        document.put("condition", MarketStore.str(product.get("condition_level")));
        return document;
    }

    private JsonNode perform(String method, String path, Object body) throws Exception {
        Request request = new Request(method, path);
        request.setJsonEntity(json.writeValueAsString(body));
        Response response = client().performRequest(request);
        try (InputStream stream = response.getEntity().getContent()) {
            return json.readTree(stream);
        }
    }

    private RestClient client() {
        RestClient current = client;
        if (current != null) {
            return current;
        }
        synchronized (this) {
            if (client == null) {
                client = RestClient.builder(HttpHost.create(url))
                        .setRequestConfigCallback(config -> config.setConnectTimeout(500).setSocketTimeout(1500))
                        .build();
            }
            return client;
        }
    }

    private void markDown(String action) {
        unavailableUntil = System.currentTimeMillis() + 15000;
        log.info("Elasticsearch 暂不可用，{}改为使用 MySQL", action);
    }
}
