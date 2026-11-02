package com.campus.market;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.stereotype.Component;

@Component
public class CaptchaService {
    private static final String ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
    private static final long TTL_SECONDS = 300;
    private final Map<String, Entry> codes = new ConcurrentHashMap<>();

    public Map<String, Object> issue() {
        Instant now = Instant.now();
        codes.entrySet().removeIf(item -> item.getValue().expiresAt.isBefore(now));
        StringBuilder code = new StringBuilder(4);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int i = 0; i < 4; i++) {
            code.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
        }
        String id = UUID.randomUUID().toString();
        codes.put(id, new Entry(code.toString(), now.plusSeconds(TTL_SECONDS)));
        return Map.of("captcha_id", id, "image", "data:image/png;base64," + png(code.toString()));
    }

    public void check(String id, String answer) {
        Entry entry = id == null ? null : codes.remove(id);
        if (entry == null || entry.expiresAt.isBefore(Instant.now()) || answer == null || !entry.code.equalsIgnoreCase(answer.trim())) {
            throw new ApiException("VALIDATION_ERROR", "验证码不正确或已过期", 422);
        }
    }

    String currentCode(String id) {
        Entry entry = codes.get(id);
        return entry == null ? "" : entry.code;
    }

    private static String png(String code) {
        BufferedImage image = new BufferedImage(128, 42, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = image.createGraphics();
        graphics.setColor(new Color(238, 242, 236));
        graphics.fillRect(0, 0, 128, 42);
        graphics.setColor(new Color(38, 59, 53));
        graphics.setFont(new Font("SansSerif", Font.BOLD, 24));
        graphics.drawString(code, 16, 29);
        graphics.dispose();
        try {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            ImageIO.write(image, "png", output);
            return Base64.getEncoder().encodeToString(output.toByteArray());
        } catch (Exception exc) {
            throw new ApiException("VALIDATION_ERROR", "验证码生成失败", 500);
        }
    }

    private record Entry(String code, Instant expiresAt) {
    }
}
