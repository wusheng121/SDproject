package com.campus.market;

import org.springframework.stereotype.Component;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.UUID;

@Component
public class ProductImageStore {
    private static final int MAX_BYTES = 4 * 1024 * 1024;
    private final Path directory = Path.of("data", "uploads");

    public void deleteIfOwned(String imageUrl) {
        if (imageUrl == null || !imageUrl.startsWith("/uploads/")) {
            return;
        }
        String name = imageUrl.substring("/uploads/".length());
        if (name.isBlank() || name.contains("..") || name.contains("/") || name.contains("\\")) {
            return;
        }
        try {
            Files.deleteIfExists(directory.resolve(name));
        } catch (Exception ignored) {
            // 商品记录已经删除，图片文件留在磁盘不影响列表。
        }
    }

    public String save(String encoded, String mime) {
        String raw = encoded == null ? "" : encoded.trim();
        int comma = raw.indexOf(',');
        if (raw.startsWith("data:") && comma >= 0) {
            raw = raw.substring(comma + 1);
        }
        byte[] bytes;
        try {
            bytes = Base64.getDecoder().decode(raw);
        } catch (IllegalArgumentException exc) {
            throw new ApiException("VALIDATION_ERROR", "图片内容无法解析", 400);
        }
        if (bytes.length == 0 || bytes.length > MAX_BYTES) {
            throw new ApiException("VALIDATION_ERROR", "图片请小于 4MB", 400);
        }
        String extension = extensionOf(bytes, mime);
        if (extension == null) {
            throw new ApiException("VALIDATION_ERROR", "图片只支持 JPEG、PNG、GIF、WebP", 400);
        }
        try {
            Files.createDirectories(directory);
            String name = UUID.randomUUID() + extension;
            Files.write(directory.resolve(name), bytes);
            return "/uploads/" + name;
        } catch (Exception exc) {
            throw new ApiException("VALIDATION_ERROR", "图片保存失败", 500);
        }
    }

    private static String extensionOf(byte[] bytes, String mime) {
        String sniffed = sniff(bytes);
        String declared = switch (mime == null ? "" : mime.split(";")[0].trim().toLowerCase()) {
            case "image/jpeg", "image/jpg" -> "jpeg";
            case "image/png" -> "png";
            case "image/gif" -> "gif";
            case "image/webp" -> "webp";
            default -> "";
        };
        String format = sniffed != null ? sniffed : declared;
        return switch (format) {
            case "jpeg" -> ".jpg";
            case "png" -> ".png";
            case "gif" -> ".gif";
            case "webp" -> ".webp";
            default -> null;
        };
    }

    private static String sniff(byte[] bytes) {
        if (bytes.length >= 3 && (bytes[0] & 0xff) == 0xff && (bytes[1] & 0xff) == 0xd8 && (bytes[2] & 0xff) == 0xff) {
            return "jpeg";
        }
        if (bytes.length >= 8 && bytes[0] == (byte) 0x89 && bytes[1] == 'P' && bytes[2] == 'N' && bytes[3] == 'G') {
            return "png";
        }
        if (bytes.length >= 6 && bytes[0] == 'G' && bytes[1] == 'I' && bytes[2] == 'F') {
            return "gif";
        }
        if (bytes.length >= 12 && bytes[0] == 'R' && bytes[1] == 'I' && bytes[2] == 'F' && bytes[3] == 'F'
                && bytes[8] == 'W' && bytes[9] == 'E' && bytes[10] == 'B' && bytes[11] == 'P') {
            return "webp";
        }
        return null;
    }
}
