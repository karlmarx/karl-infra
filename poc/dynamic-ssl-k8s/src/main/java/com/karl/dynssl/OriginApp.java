package com.karl.dynssl;

import com.sun.net.httpserver.HttpsConfigurator;
import com.sun.net.httpserver.HttpsServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;

/**
 * Stand-in for a third-party HTTPS API. Presents a server certificate loaded from a
 * mounted PKCS12 keystore (a Kubernetes Secret). "Rotating the CA" == swapping that
 * Secret for a keystore signed by a different CA and restarting this deployment.
 *
 * The whole point of the PoC is that the CALLER survives that rotation without a restart;
 * the origin restarting is expected and realistic (the third party controls its own certs).
 */
public final class OriginApp {

    private static final Logger log = LoggerFactory.getLogger(OriginApp.class);

    public static void run() throws Exception {
        Path keystore = Path.of(App.env("KEYSTORE_PATH", "/etc/ssl/origin/keystore.p12"));
        char[] password = App.env("KEYSTORE_PASSWORD", "changeit").toCharArray();
        int port = Integer.parseInt(App.env("PORT", "8443"));
        String certLabel = App.env("CERT_LABEL", "unknown-ca");

        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (InputStream in = Files.newInputStream(keystore)) {
            ks.load(in, password);
        }
        KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        kmf.init(ks, password);

        SSLContext ctx = SSLContext.getInstance("TLS");
        ctx.init(kmf.getKeyManagers(), null, null);

        HttpsServer server = HttpsServer.create(new InetSocketAddress(port), 0);
        server.setHttpsConfigurator(new HttpsConfigurator(ctx));
        server.createContext("/", ex -> {
            String body = String.format(
                    "{\"service\":\"third-party-origin\",\"servingCert\":\"%s\",\"message\":\"hello over TLS\"}",
                    certLabel);
            byte[] b = body.getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().set("Content-Type", "application/json");
            ex.sendResponseHeaders(200, b.length);
            try (var os = ex.getResponseBody()) {
                os.write(b);
            }
        });
        server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(4));
        server.start();
        log.info("Origin HTTPS server listening on :{}  (serving cert signed by {})", port, certLabel);
        Thread.currentThread().join();
    }
}
