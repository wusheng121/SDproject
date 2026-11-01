package com.campus.market;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestControllerAdvice
public class ApiAdvice {
    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Map<String, Object>> handle(ApiException exc) {
        Map<String, Object> error = new LinkedHashMap<>();
        error.put("code", exc.getCode());
        error.put("message", exc.getMessage());
        error.put("details", List.of());
        error.put("trace_id", null);
        return ResponseEntity.status(exc.getStatus()).body(Map.of("error", error));
    }
}
