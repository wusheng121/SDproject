package com.campus.market;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class AdminBootstrap {
    private static final Logger log = LoggerFactory.getLogger(AdminBootstrap.class);

    private final MarketStore store;
    private final Tokens tokens;

    public AdminBootstrap(MarketStore store, Tokens tokens) {
        this.store = store;
        this.tokens = tokens;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootstrap() {
        String username = trim(read("BOOTSTRAP_ADMIN_USERNAME"));
        String email = trim(read("BOOTSTRAP_ADMIN_EMAIL"));
        String password = read("BOOTSTRAP_ADMIN_PASSWORD");
        if (username.isBlank() && email.isBlank() && (password == null || password.isBlank())) {
            return;
        }
        if (store.countAdmins() > 0) {
            log.info("admin bootstrap skipped: an administrator already exists");
            return;
        }
        if (username.isBlank() || email.isBlank() || password == null || password.length() < 8) {
            log.warn("admin bootstrap skipped: BOOTSTRAP_ADMIN_USERNAME/EMAIL/PASSWORD are incomplete");
            return;
        }
        if (store.findUser(username) != null || store.findUser(email) != null) {
            log.warn("admin bootstrap skipped: account already exists");
            return;
        }
        store.bootstrapAdmin(username, email, tokens.hashPassword(password));
        log.info("initial administrator created: {}", username);
    }

    private static String trim(String value) {
        return value == null ? "" : value.trim();
    }

    private static String read(String name) {
        String property = System.getProperty(name);
        return property != null ? property : System.getenv(name);
    }
}
