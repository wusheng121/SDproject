package com.campus.market;

import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Arrays;
import java.util.Base64;

@Component
public class PhoneCipher {
    private final byte[] signingKey;
    private final byte[] encryptionKey;
    private final byte[] hashKey;
    private final SecureRandom random = new SecureRandom();

    public PhoneCipher(CampusProperties properties) {
        byte[] key = fernetKey(properties);
        this.signingKey = Arrays.copyOfRange(key, 0, 16);
        this.encryptionKey = Arrays.copyOfRange(key, 16, 32);
        String hashMaterial = properties.getPhoneHashKey();
        if (hashMaterial == null || hashMaterial.isBlank()) {
            hashMaterial = properties.getJwtSecret() == null ? "" : properties.getJwtSecret();
        }
        this.hashKey = hashMaterial.getBytes(StandardCharsets.UTF_8);
    }

    public String encrypt(String phone) {
        String normalized = normalize(phone);
        if (normalized == null) {
            return null;
        }
        try {
            byte[] iv = new byte[16];
            random.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(encryptionKey, "AES"), new IvParameterSpec(iv));
            byte[] ciphertext = cipher.doFinal(normalized.getBytes(StandardCharsets.UTF_8));
            ByteBuffer packed = ByteBuffer.allocate(1 + 8 + iv.length + ciphertext.length);
            packed.put((byte) 0x80);
            packed.putLong(Instant.now().getEpochSecond());
            packed.put(iv);
            packed.put(ciphertext);
            byte[] body = packed.array();
            byte[] mac = hmac(body);
            byte[] token = Arrays.copyOf(body, body.length + mac.length);
            System.arraycopy(mac, 0, token, body.length, mac.length);
            return Base64.getUrlEncoder().encodeToString(token);
        } catch (Exception exc) {
            throw new IllegalStateException("手机号加密失败", exc);
        }
    }

    public String decrypt(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        try {
            byte[] data = Base64.getUrlDecoder().decode(token);
            if (data.length < 1 + 8 + 16 + 32 || data[0] != (byte) 0x80) {
                return null;
            }
            byte[] body = Arrays.copyOf(data, data.length - 32);
            byte[] expected = hmac(body);
            byte[] actual = Arrays.copyOfRange(data, data.length - 32, data.length);
            if (!MessageDigest.isEqual(expected, actual)) {
                return null;
            }
            byte[] iv = Arrays.copyOfRange(data, 9, 25);
            byte[] ciphertext = Arrays.copyOfRange(data, 25, data.length - 32);
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(encryptionKey, "AES"), new IvParameterSpec(iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (Exception exc) {
            return null;
        }
    }

    public String hash(String phone) {
        String normalized = normalize(phone);
        if (normalized == null) {
            return null;
        }
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(hashKey, "HmacSHA256"));
            byte[] digest = mac.doFinal(normalized.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(digest.length * 2);
            for (byte value : digest) {
                hex.append(String.format("%02x", value));
            }
            return hex.toString();
        } catch (Exception exc) {
            throw new IllegalStateException("手机号摘要失败", exc);
        }
    }

    public static String normalize(String phone) {
        if (phone == null || phone.isBlank()) {
            return null;
        }
        StringBuilder cleaned = new StringBuilder();
        for (int i = 0; i < phone.length(); i++) {
            char ch = phone.charAt(i);
            if (Character.isDigit(ch) || ch == '+') {
                cleaned.append(ch);
            }
        }
        String value = cleaned.toString();
        if (value.startsWith("00")) {
            value = "+" + value.substring(2);
        }
        String digits = value.startsWith("+") ? value.substring(1) : value;
        if (!digits.chars().allMatch(Character::isDigit) || digits.length() < 6 || digits.length() > 15) {
            return null;
        }
        return value;
    }

    public static String mask(String phone) {
        if (phone == null || phone.isBlank()) {
            return null;
        }
        StringBuilder digits = new StringBuilder();
        for (int i = 0; i < phone.length(); i++) {
            if (Character.isDigit(phone.charAt(i))) {
                digits.append(phone.charAt(i));
            }
        }
        String value = digits.toString();
        if (value.length() == 13 && value.startsWith("86")) {
            value = value.substring(2);
        }
        if (value.length() >= 11) {
            return value.substring(0, 3) + "****" + value.substring(value.length() - 4);
        }
        if (value.length() >= 7) {
            return value.substring(0, 2) + "***" + value.substring(value.length() - 2);
        }
        return "***";
    }

    public String opaqueToken() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private byte[] hmac(byte[] body) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(signingKey, "HmacSHA256"));
        return mac.doFinal(body);
    }

    private static byte[] fernetKey(CampusProperties properties) {
        String configured = properties.getPhoneEncKey() == null ? "" : properties.getPhoneEncKey().trim();
        if (!configured.isEmpty()) {
            try {
                byte[] decoded = Base64.getUrlDecoder().decode(configured);
                if (decoded.length == 32) {
                    return decoded;
                }
            } catch (IllegalArgumentException ignored) {
                // 和原来的 Python 一样，密钥不是 Fernet 格式时改用它的摘要。
            }
        }
        String material = configured.isEmpty() ? properties.getJwtSecret() : configured;
        if (material == null) {
            material = "";
        }
        try {
            return MessageDigest.getInstance("SHA-256").digest(material.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exc) {
            throw new IllegalStateException(exc);
        }
    }
}
