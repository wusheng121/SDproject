package com.campus.market;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class MarketApplication {
    public static void main(String[] args) {
        BackendEnv.load();
        SpringApplication.run(MarketApplication.class, args);
    }
}
