package com.campus.market;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InputSafetyTest {
    @Test
    void searchTextStaysABoundParameter() {
        StringBuilder sql = new StringBuilder("SELECT p.* FROM products p WHERE p.status = 'approved'");
        List<Object> args = new ArrayList<>();
        MarketStore.appendFilters(sql, args, null, "' OR 1=1 --", null, null, null);
        assertTrue(sql.toString().contains("LIKE ?"));
        assertFalse(sql.toString().contains("OR 1=1"));
        assertEquals("%' OR 1=1 --%", args.get(0));
    }

    @Test
    void captchaIsSingleUse() {
        CaptchaService captcha = new CaptchaService();
        Map<String, Object> issued = captcha.issue();
        String id = String.valueOf(issued.get("captcha_id"));
        String code = captcha.currentCode(id);
        assertTrue(String.valueOf(issued.get("image")).startsWith("data:image/png;base64,"));
        captcha.check(id, code);
        assertThrows(ApiException.class, () -> captcha.check(id, code));
    }

    @Test
    void naturalLanguagePathIsForwardedToTheDataServer() {
        assertTrue(DataProxy.isDataPath("/api/ai/filter/nl"));
        assertTrue(DataProxy.isDataPath("/api/recommendations/quality"));
        assertTrue(DataProxy.isDataPath("/api/ai/recognize-query"));
    }
}
