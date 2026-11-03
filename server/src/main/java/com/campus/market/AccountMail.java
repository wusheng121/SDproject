package com.campus.market;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

@Component
public class AccountMail {
    private static final Logger log = LoggerFactory.getLogger(AccountMail.class);

    private final CampusProperties properties;
    private final JavaMailSender mailSender;

    public AccountMail(CampusProperties properties, JavaMailSender mailSender) {
        this.properties = properties;
        this.mailSender = mailSender;
    }

    public void sendVerification(String email, String token) {
        String link = properties.getFrontendUrl() + "/verify-email?token=" + token;
        send(email, "验证你的校园二手交易平台邮箱", "请打开以下链接完成邮箱验证：\n" + link);
    }

    public void sendPasswordReset(String email, String token) {
        String link = properties.getFrontendUrl() + "/reset-password?token=" + token;
        send(email, "重置你的校园二手交易平台密码", "请打开以下链接重置密码：\n" + link);
    }

    private void send(String email, String subject, String text) {
        String host = properties.getSmtpHost();
        if (host == null || host.isBlank()) {
            log.info("mail skipped: SMTP_HOST is empty. to={} subject={} body={}", email, subject, text);
            return;
        }
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(properties.getMailFrom());
            message.setTo(email);
            message.setSubject(subject);
            message.setText(text);
            mailSender.send(message);
            log.info("mail sent via {}:{} to={} subject={}", host, properties.getSmtpPort(), email, subject);
        } catch (Exception exc) {
            log.warn("mail failed via {}:{} to={} subject={} body={}", host, properties.getSmtpPort(), email, subject, text, exc);
        }
    }
}
