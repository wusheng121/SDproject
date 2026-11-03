package com.campus.market;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class ProductEventPublisher {
    private static final Logger log = LoggerFactory.getLogger(ProductEventPublisher.class);
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private final ProductEventSink sink;
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    @Autowired
    public ProductEventPublisher(ObjectProvider<RabbitTemplate> templates, JdbcTemplate jdbc, ObjectMapper mapper) {
        RabbitTemplate template = templates.getIfAvailable();
        this.sink = template == null ? body -> { } : body -> template.convertAndSend(
                ProductQueueConfig.EXCHANGE, ProductQueueConfig.ROUTING_KEY, body);
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    ProductEventPublisher(ProductEventSink sink) {
        this.sink = sink;
        this.jdbc = null;
        this.mapper = null;
    }

    public void publish(long productId, String status) {
        String eventId = productId + ":" + status + ":" + System.currentTimeMillis();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("product_id", productId);
        body.put("status", status);
        body.put("event_id", eventId);
        if (jdbc != null && mapper != null) {
            try {
                jdbc.update("""
                        INSERT INTO product_outbox (event_id, payload_json, status, retry_count, created_at)
                        VALUES (?, ?, 'pending', 0, ?)
                        """, eventId, mapper.writeValueAsString(body), LocalDateTime.now().format(STAMP));
            } catch (Exception exc) {
                log.warn("商品事件 outbox 写入失败: {}", eventId, exc);
            }
        }
        try {
            sink.send(body);
            markSent(eventId);
        } catch (RuntimeException exc) {
            log.info("商品消息暂未发送，已保存到 outbox: product={} status={}", productId, status);
        }
    }

    @Scheduled(fixedDelay = 30000)
    public void retryPending() {
        if (jdbc == null || mapper == null) {
            return;
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, event_id, payload_json, retry_count
                FROM product_outbox
                WHERE status = 'pending'
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY id LIMIT 50
                """, LocalDateTime.now().format(STAMP));
        for (Map<String, Object> row : rows) {
            String eventId = String.valueOf(row.get("event_id"));
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> body = mapper.readValue(String.valueOf(row.get("payload_json")), Map.class);
                sink.send(body);
                markSent(eventId);
            } catch (Exception exc) {
                int retries = ((Number) row.get("retry_count")).intValue() + 1;
                jdbc.update("""
                        UPDATE product_outbox
                        SET retry_count = ?, next_retry_at = ?
                        WHERE event_id = ?
                        """, retries,
                        LocalDateTime.now().plusSeconds(Math.min(300, retries * 15)).format(STAMP),
                        eventId);
            }
        }
    }

    private void markSent(String eventId) {
        if (jdbc == null) {
            return;
        }
        jdbc.update("UPDATE product_outbox SET status = 'sent', sent_at = ? WHERE event_id = ?",
                LocalDateTime.now().format(STAMP), eventId);
    }

    interface ProductEventSink {
        void send(Map<String, Object> body);
    }
}
