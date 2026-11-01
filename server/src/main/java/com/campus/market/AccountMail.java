package com.campus.market;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

@Component
public class AccountMail {
    private static final Logger log = LoggerFactory.getLogger(AccountMail.class);
    private final CampusProperties properties;

    public AccountMail(CampusProperties properties) {
        this.properties = properties;
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
            host = "127.0.0.1";
        }
        try (Socket socket = new Socket(host, properties.getSmtpPort())) {
            socket.setSoTimeout(10000);
            OutputStream out = socket.getOutputStream();
            read(socket);
            write(out, "EHLO campus-market\r\n");
            read(socket);
            write(out, "MAIL FROM:<" + properties.getMailFrom() + ">\r\n");
            read(socket);
            write(out, "RCPT TO:<" + email + ">\r\n");
            read(socket);
            write(out, "DATA\r\n");
            read(socket);
            String message = "From: " + properties.getMailFrom() + "\r\n"
                    + "To: " + email + "\r\n"
                    + "Subject: " + subject + "\r\n"
                    + "\r\n"
                    + text + "\r\n.\r\n";
            write(out, message);
            read(socket);
            write(out, "QUIT\r\n");
            log.info("mail sent via {}:{} to={} subject={}", host, properties.getSmtpPort(), email, subject);
        } catch (Exception exc) {
            log.info("mail failed, open MailHog at http://127.0.0.1:8025 or use the link: to={} subject={} body={}", email, subject, text);
        }
    }

    private static void write(OutputStream out, String line) throws Exception {
        out.write(line.getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    private static void read(Socket socket) throws Exception {
        byte[] buffer = new byte[1024];
        socket.getInputStream().read(buffer);
    }
}
