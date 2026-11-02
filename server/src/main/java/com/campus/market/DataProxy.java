package com.campus.market;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@RestController
@EnableConfigurationProperties(CampusProperties.class)
public class DataProxy {
    private static final Set<String> HOP_HEADERS = Set.of(
            "host", "connection", "content-length", "transfer-encoding", "keep-alive"
    );

    private final String dataRoot;
    private final RestClient dataClient;

    public DataProxy(CampusProperties properties) {
        String root = properties.getDataUrl();
        if (root.endsWith("/")) {
            root = root.substring(0, root.length() - 1);
        }
        this.dataRoot = root;
        this.dataClient = RestClient.builder().baseUrl(root).build();
    }

    static boolean isDataPath(String path) {
        if (path == null) {
            return false;
        }
        return path.startsWith("/api/recommendations")
                || path.startsWith("/api/v1/assistant")
                || path.startsWith("/api/ai/")
                || path.startsWith("/api/products/price-reference");
    }

    @RequestMapping({
            "/api/recommendations",
            "/api/recommendations/**",
            "/api/v1/assistant",
            "/api/v1/assistant/**",
            "/api/ai/**",
            "/api/products/price-reference"
    })
    public ResponseEntity<byte[]> forward(HttpServletRequest request) throws IOException {
        byte[] body = StreamUtils.copyToByteArray(request.getInputStream());
        return dataClient.method(HttpMethod.valueOf(request.getMethod()))
                .uri(forwardedUri(dataRoot, request.getRequestURI(), request.getQueryString()))
                .headers(headers -> copyRequestHeaders(request, headers))
                .body(body)
                .exchange((req, res) -> {
                    HttpHeaders outbound = new HttpHeaders();
                    res.getHeaders().forEach((name, values) -> {
                        if (!HOP_HEADERS.contains(name.toLowerCase(Locale.ROOT))) {
                            outbound.addAll(name, values);
                        }
                    });
                    return ResponseEntity.status(res.getStatusCode()).headers(outbound).body(res.getBody().readAllBytes());
                });
    }

    static URI forwardedUri(String root, String requestUri, String query) {
        String base = root.endsWith("/") ? root.substring(0, root.length() - 1) : root;
        String raw = base + (requestUri == null ? "" : requestUri);
        if (query != null && !query.isBlank()) {
            raw = raw + "?" + query;
        }
        return URI.create(raw);
    }

    private static void copyRequestHeaders(HttpServletRequest request, HttpHeaders headers) {
        List<String> names = java.util.Collections.list(request.getHeaderNames());
        for (String name : names) {
            if (HOP_HEADERS.contains(name.toLowerCase(Locale.ROOT))) {
                continue;
            }
            headers.addAll(name, java.util.Collections.list(request.getHeaders(name)));
        }
    }
}
