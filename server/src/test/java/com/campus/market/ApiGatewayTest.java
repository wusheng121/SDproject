package com.campus.market;

import org.junit.jupiter.api.Test;

import java.net.URI;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ApiGatewayTest {
    @Test
    void recommendationVisionAndAssistantGoToThePythonDataServer() {
        assertTrue(DataProxy.isDataPath("/api/recommendations"));
        assertTrue(DataProxy.isDataPath("/api/recommendations/similar/3"));
        assertTrue(DataProxy.isDataPath("/api/v1/assistant/chat"));
        assertTrue(DataProxy.isDataPath("/api/ai/listing-recognize"));
        assertTrue(DataProxy.isDataPath("/api/products/price-reference"));
    }

    @Test
    void accountsProductsCartAndOrdersStayOnTheBusinessServer() {
        assertFalse(DataProxy.isDataPath("/api/v1/auth/login"));
        assertFalse(DataProxy.isDataPath("/api/v1/cart"));
        assertFalse(DataProxy.isDataPath("/api/v1/orders"));
        assertFalse(DataProxy.isDataPath("/api/products"));
        assertFalse(DataProxy.isDataPath("/api/v1/admin/users"));
    }

    @Test
    void chineseQueryIsForwardedWithoutASecondEncoding() {
        URI uri = DataProxy.forwardedUri(
                "http://127.0.0.1:5001",
                "/api/products/price-reference",
                "category=%E5%8F%B0%E7%81%AF");
        assertEquals("http://127.0.0.1:5001/api/products/price-reference?category=%E5%8F%B0%E7%81%AF", uri.toASCIIString());
    }
}
