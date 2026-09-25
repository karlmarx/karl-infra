package com.karl.dynssl;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.stream.Collectors;

/**
 * The microservice under test. Exposes a tiny plain-HTTP control API (so the demo script
 * can poke it) and owns the single {@link DynamicTrustHttpClient} plus the file-watcher.
 *
 *   GET  /healthz        -> liveness
 *   GET  /trust/info     -> issuer count + bundle sha (proves what it currently trusts)
 *   GET  /call?url=...   -> outbound HTTPS GET via the dynamically-trusted RestTemplate
 *   POST /trust/reload   -> manual ("push") reload, in addition to the file-watcher
 */
public final class CallerApp {

    private static final Logger log = LoggerFactory.getLogger(CallerApp.class);

    public static void run() throws Exception {
        Path bundleDir = Path.of(App.env("CA_BUNDLE_DIR", "/etc/ssl/ca-bundle"));
        Path bundleFile = bundleDir.resolve(App.env("CA_BUNDLE_FILE", "ca-bundle.pem"));
        int port = Integer.parseInt(App.env("PORT", "8080"));

        DynamicTrustHttpClient client = new DynamicTrustHttpClient(bundleFile);

        // Hot-reload trust whenever the mounted ConfigMap changes (no restart).
        Thread watcher = new Thread(new CaBundleWatcher(bundleDir, client::reloadTrust), "ca-bundle-watcher");
        watcher.setDaemon(true);
        watcher.start();

        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);

        server.createContext("/healthz", ex -> respond(ex, 200, "{\"status\":\"ok\"}"));

        server.createContext("/trust/info", ex -> {
            // acceptedIssuerCount is the FULL trust set (JDK defaults + bundle). We surface
            // only the PoC's own CAs ("DynSSL...") so the demo output stays readable while
            // still proving the bundle's CAs flipped from {CA-A} to {CA-A, CA-B}.
            String pocIssuers = client.acceptedIssuerNames().stream()
                    .filter(n -> n.contains("DynSSL"))
                    .map(CallerApp::jsonString)
                    .collect(Collectors.joining(","));
            respond(ex, 200, String.format(
                    "{\"acceptedIssuerCount\":%d,\"bundleSha256\":%s,\"bundlePath\":%s,\"pocIssuers\":[%s]}",
                    client.acceptedIssuerCount(), jsonString(client.bundleSha256()),
                    jsonString(client.bundlePath().toString()), pocIssuers));
        });

        server.createContext("/trust/reload", ex -> {
            if (!"POST".equalsIgnoreCase(ex.getRequestMethod())) {
                respond(ex, 405, "{\"error\":\"use POST\"}");
                return;
            }
            try {
                client.reloadTrust();
                respond(ex, 200, String.format(
                        "{\"reloaded\":true,\"acceptedIssuerCount\":%d,\"bundleSha256\":%s}",
                        client.acceptedIssuerCount(), jsonString(client.bundleSha256())));
            } catch (Exception e) {
                respond(ex, 500, "{\"reloaded\":false,\"error\":" + jsonString(String.valueOf(e.getMessage())) + "}");
            }
        });

        server.createContext("/call", ex -> {
            String url = queryParam(ex, "url");
            if (url == null) {
                respond(ex, 400, "{\"error\":\"missing ?url=\"}");
                return;
            }
            try {
                String body = client.get(url);
                String preview = body == null ? "" : body.replaceAll("\\s+", " ").trim();
                if (preview.length() > 200) preview = preview.substring(0, 200);
                respond(ex, 200, String.format("{\"ok\":true,\"url\":%s,\"body\":%s}",
                        jsonString(url), jsonString(preview)));
            } catch (Exception e) {
                // The PKIX failure on CA rotation surfaces right here.
                Throwable root = e;
                while (root.getCause() != null) root = root.getCause();
                String msg = e.getClass().getSimpleName() + ": " + e.getMessage()
                        + " | root=" + root.getClass().getSimpleName() + ": " + root.getMessage();
                log.warn("Outbound call to {} FAILED: {}", url, msg);
                // Always HTTP 200 for this diagnostic endpoint — the outbound result lives in
                // the JSON "ok" field. (Avoids busybox wget swallowing the body on non-2xx.)
                respond(ex, 200, String.format("{\"ok\":false,\"url\":%s,\"error\":%s}",
                        jsonString(url), jsonString(msg)));
            }
        });

        server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(8));
        server.start();
        log.info("Caller control API listening on :{}  (bundle={})", port, bundleFile);
        Thread.currentThread().join();
    }

    // --- tiny helpers (no JSON lib needed for a PoC) ---

    private static String queryParam(HttpExchange ex, String name) {
        String q = ex.getRequestURI().getRawQuery();
        if (q == null) return null;
        for (String pair : q.split("&")) {
            int i = pair.indexOf('=');
            if (i > 0 && pair.substring(0, i).equals(name)) {
                return java.net.URLDecoder.decode(pair.substring(i + 1), StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private static void respond(HttpExchange ex, int code, String body) {
        try {
            byte[] b = body.getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().set("Content-Type", "application/json");
            ex.sendResponseHeaders(code, b.length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(b);
            }
        } catch (Exception ignored) {
        }
    }

    private static String jsonString(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> sb.append(c);
            }
        }
        return sb.append("\"").toString();
    }
}
