package com.campus.market;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ProductQueueConfig {
    public static final String EXCHANGE = "campus.product";
    public static final String QUEUE = "campus.product.cache";
    public static final String ROUTING_KEY = "product.changed";

    @Bean
    public TopicExchange productExchange() {
        return new TopicExchange(EXCHANGE, true, false);
    }

    @Bean
    public Queue productCacheQueue() {
        return QueueBuilder.durable(QUEUE).build();
    }

    @Bean
    public Binding productCacheBinding(Queue productCacheQueue, TopicExchange productExchange) {
        return BindingBuilder.bind(productCacheQueue).to(productExchange).with(ROUTING_KEY);
    }
}
