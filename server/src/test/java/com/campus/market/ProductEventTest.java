package com.campus.market;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ProductEventTest {
    @Test
    void duplicateEventIsIgnored() {
        ProductCacheListener listener = new ProductCacheListener(null, null, null);
        assertTrue(listener.firstTime("9:sold:1"));
        assertFalse(listener.firstTime("9:sold:1"));
    }

    @Test
    void publishKeepsTheDatabaseChangeWhenTheQueueIsDown() {
        ProductEventPublisher publisher = new ProductEventPublisher(body -> {
            throw new IllegalStateException("rabbit down");
        });
        assertDoesNotThrow(() -> publisher.publish(9, "sold"));
    }

    @Test
    void blankSearchAddressFallsBackToMysql() {
        ProductSearchIndex index = new ProductSearchIndex("", null);
        assertTrue(index.findIds("手机") == null);
    }
}
