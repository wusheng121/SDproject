package com.campus.market;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MarketApplication {
    public static void main(String[] args) {
        BackendEnv.load();
        SpringApplication.run(MarketApplication.class, args);
    }
}
