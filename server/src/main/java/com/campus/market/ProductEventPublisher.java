package com.campus.market;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class ProductEventPublisher {
    private static final Logger log = LoggerFactory.getLogger(ProductEventPublisher.class);
    private final ProductEventSink sink;

    @Autowired
    public ProductEventPublisher(ObjectProvider<RabbitTemplate> templates) {
        RabbitTemplate template = templates.getIfAvailable();
        this.sink = template == null ? body -> { } : body -> template.convertAndSend(
                ProductQueueConfig.EXCHANGE, ProductQueueConfig.ROUTING_KEY, body);
    }

    ProductEventPublisher(ProductEventSink sink) {
        this.sink = sink;
    }

    public void publish(long productId, String status) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("product_id", productId);
        body.put("status", status);
        body.put("event_id", productId + ":" + status + ":" + System.currentTimeMillis());
        try {
            sink.send(body);
        } catch (RuntimeException exc) {
            log.info("商品消息未发出，数据库修改已保留: product={} status={}", productId, status);
        }
    }

    interface ProductEventSink {
        void send(Map<String, Object> body);
    }
}
