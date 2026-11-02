package com.campus.market;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class PhoneCipherTest {
    @Test
    void encryptsAndMasksLikeTheExistingAccountRules() throws Exception {
        PhoneCipher cipher = cipher();
        assertEquals("13800138000", cipher.decrypt(cipher.encrypt("13800138000")));
        assertEquals("138****8000", PhoneCipher.mask("13800138000"));
        assertNull(cipher.encrypt("abc"));

        Path python = Path.of("..", "backend", ".venv", "Scripts", "python.exe");
        if (!Files.exists(python)) {
            return;
        }
        String pyToken = run(python, "enc", "13800138000").trim();
        assertEquals("13800138000", cipher.decrypt(pyToken));
        String javaToken = cipher.encrypt("13900001111");
        assertEquals("13900001111", run(python, "dec", javaToken).trim());
    }

    private static String run(Path python, String mode, String value) throws Exception {
        Path script = Files.createTempFile("phone-fernet", ".py");
        Files.writeString(script, """
                import hashlib, base64, sys
                from cryptography.fernet import Fernet
                key = base64.urlsafe_b64encode(hashlib.sha256(b"dev-only-change-me-0123456789abcdef").digest())
                box = Fernet(key)
                if sys.argv[1] == "enc":
                    print(box.encrypt(sys.argv[2].encode()).decode())
                else:
                    print(box.decrypt(sys.argv[2].encode()).decode())
                """);
        Process process = new ProcessBuilder(python.toString(), script.toString(), mode, value)
                .redirectErrorStream(true)
                .start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        if (process.waitFor() != 0) {
            throw new IllegalStateException(output);
        }
        return output;
    }

    private static PhoneCipher cipher() {
        CampusProperties properties = new CampusProperties();
        properties.setJwtSecret("dev-only-change-me-0123456789abcdef");
        return new PhoneCipher(properties);
    }
}
