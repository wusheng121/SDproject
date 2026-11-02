package com.campus.market;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class ProductCacheListener {
    private final CatalogCache cache;
    private final MarketStore store;
    private final ProductSearchIndex searchIndex;
    private final Map<String, Boolean> seen = new LinkedHashMap<>(256, 0.75f, false) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Boolean> eldest) {
            return size() > 500;
        }
    };

    public ProductCacheListener(CatalogCache cache, MarketStore store, ProductSearchIndex searchIndex) {
        this.cache = cache;
        this.store = store;
        this.searchIndex = searchIndex;
    }

    @RabbitListener(queues = ProductQueueConfig.QUEUE)
    public void onProductChanged(Map<String, Object> message) {
        String eventId = String.valueOf(message.get("event_id"));
        if (!firstTime(eventId)) {
            return;
        }
        long productId = ((Number) message.get("product_id")).longValue();
        cache.invalidate("product:" + productId);
        for (String name : store.categoriesOf(productId)) {
            cache.invalidate("price:" + name);
        }
        if (searchIndex != null) {
            searchIndex.sync(productId);
        }
    }

    synchronized boolean firstTime(String eventId) {
        if (eventId == null || eventId.isBlank() || "null".equals(eventId) || seen.containsKey(eventId)) {
            return false;
        }
        seen.put(eventId, Boolean.TRUE);
        return true;
    }
}
