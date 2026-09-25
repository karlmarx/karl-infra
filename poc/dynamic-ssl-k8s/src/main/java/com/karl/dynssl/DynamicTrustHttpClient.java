package com.karl.dynssl;

import nl.altindag.ssl.SSLFactory;
import nl.altindag.ssl.apache4.util.Apache4SslUtils;
import nl.altindag.ssl.util.SSLFactoryUtils;
import org.apache.http.config.RegistryBuilder;
import org.apache.http.conn.socket.ConnectionSocketFactory;
import org.apache.http.conn.socket.LayeredConnectionSocketFactory;
import org.apache.http.conn.socket.PlainConnectionSocketFactory;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The heart of the PoC.
 *
 * One STABLE object graph is built ONCE:
 *     SSLFactory (swappable trust) -> Apache LayeredConnectionSocketFactory
 *         -> PoolingHttpClientConnectionManager -> CloseableHttpClient -> RestTemplate
 *
 * None of those objects is ever recreated. When the CA bundle on disk changes,
 * {@link #reloadTrust()} atomically swaps the inner X509ExtendedTrustManager under a
 * write lock (Ayza's HotSwappableX509ExtendedTrustManager) and invalidates the SSL
 * session cache. New handshakes immediately use the new CAs; the pool, the socket
 * factory and the SSLContext reference are untouched — so NO restart is needed.
 */
public final class DynamicTrustHttpClient {

    private static final Logger log = LoggerFactory.getLogger(DynamicTrustHttpClient.class);

    private final Path bundlePath;
    private final SSLFactory baseSslFactory;     // STABLE — created once, swapped internally
    private final RestTemplate restTemplate;     // STABLE — created once
    private final AtomicReference<String> bundleSha = new AtomicReference<>("");

    public DynamicTrustHttpClient(Path bundlePath) {
        this.bundlePath = bundlePath;

        // 1) One stable SSLFactory: JDK defaults + the rotating third-party CA bundle,
        //    with the trust material made swappable.
        this.baseSslFactory = SSLFactory.builder()
                .withDefaultTrustMaterial()                  // keep trusting the public web PKI
                .withTrustMaterial(loadBundle())             // the rotating third-party CA bundle
                .withSwappableTrustMaterial()                // -> HotSwappableX509ExtendedTrustManager
                .build();

        // 2) Apache HttpClient 4 socket factory bound to the STABLE SSLContext.
        LayeredConnectionSocketFactory sslSocketFactory =
                Apache4SslUtils.toSocketFactory(baseSslFactory);

        PoolingHttpClientConnectionManager cm = new PoolingHttpClientConnectionManager(
                RegistryBuilder.<ConnectionSocketFactory>create()
                        .register("https", sslSocketFactory)
                        .register("http", PlainConnectionSocketFactory.getSocketFactory())
                        .build());
        cm.setMaxTotal(200);
        cm.setDefaultMaxPerRoute(20);

        CloseableHttpClient httpClient = HttpClients.custom()
                .setConnectionManager(cm)
                .setSSLHostnameVerifier(baseSslFactory.getHostnameVerifier())
                .build();

        // 3) Spring RestTemplate over that one Apache HttpClient 4 instance.
        this.restTemplate = new RestTemplate(new HttpComponentsClientHttpRequestFactory(httpClient));

        log.info("DynamicTrustHttpClient ready. Trusting {} issuers from bundle {} (sha256={})",
                acceptedIssuerCount(), bundlePath, bundleSha.get());
    }

    /** Perform an outbound HTTPS GET through the stable, dynamically-trusted client. */
    public String get(String url) {
        return restTemplate.getForObject(url, String.class);
    }

    /**
     * Called by the file-watcher (or the /trust/reload admin endpoint) when the bundle
     * on disk changes. Atomic, lock-guarded swap — the RestTemplate keeps working.
     */
    public synchronized void reloadTrust() {
        SSLFactory updated = SSLFactory.builder()
                .withDefaultTrustMaterial()
                .withTrustMaterial(loadBundle())
                .build();
        SSLFactoryUtils.reload(baseSslFactory, updated);   // swap TM under write lock + invalidate caches
        log.info("Trust reloaded. Now trusting {} issuers (bundle sha256={})",
                acceptedIssuerCount(), bundleSha.get());
    }

    public int acceptedIssuerCount() {
        return baseSslFactory.getTrustManager()
                .map(tm -> tm.getAcceptedIssuers().length)
                .orElse(0);
    }

    public List<String> acceptedIssuerNames() {
        List<String> names = new ArrayList<>();
        baseSslFactory.getTrustManager().ifPresent(tm -> {
            for (X509Certificate c : tm.getAcceptedIssuers()) {
                names.add(c.getSubjectX500Principal().getName());
            }
        });
        return names;
    }

    public String bundleSha256() {
        return bundleSha.get();
    }

    public Path bundlePath() {
        return bundlePath;
    }

    /**
     * Build an in-memory trust KeyStore from the PEM bundle on disk. Parsing the PEM with
     * the JDK CertificateFactory keeps the ConfigMap human-readable PEM text (no binary
     * keystore in the ConfigMap) and avoids pulling an extra Ayza PEM module.
     */
    private KeyStore loadBundle() {
        try {
            byte[] raw = Files.readAllBytes(bundlePath);
            bundleSha.set(sha256(raw));

            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            Collection<? extends Certificate> certs;
            try (InputStream in = Files.newInputStream(bundlePath)) {
                certs = cf.generateCertificates(in);
            }

            KeyStore ks = KeyStore.getInstance("PKCS12");
            ks.load(null, null);
            int i = 0;
            for (Certificate c : certs) {
                ks.setCertificateEntry("ca-" + (i++), c);
            }
            if (i == 0) {
                log.warn("CA bundle {} contained zero certificates", bundlePath);
            }
            return ks;
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load CA bundle from " + bundlePath, e);
        }
    }

    private static String sha256(byte[] data) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(data);
            StringBuilder sb = new StringBuilder();
            for (byte b : d) sb.append(String.format("%02x", b));
            return sb.substring(0, 16); // short prefix is plenty for the demo
        } catch (Exception e) {
            return "?";
        }
    }
}
