package com.karl.dynssl;

/**
 * Single image, two roles — selected by the APP_MODE env var so the whole PoC
 * ships as one container build.
 *
 *   APP_MODE=caller  -> the dynamic-trust microservice (Apache HttpClient 4 + Ayza
 *                       swappable trust material + a ConfigMap file-watcher). This is
 *                       the thing under test: it must keep working across a CA rotation
 *                       WITHOUT a pod restart.
 *
 *   APP_MODE=origin  -> a stand-in "third-party API": a plain HTTPS server presenting a
 *                       server cert from a mounted keystore. Rotating its CA == swapping
 *                       the keystore Secret + restarting this deployment (expected — the
 *                       third party is allowed to restart; the caller is not).
 */
public final class App {
    public static void main(String[] args) throws Exception {
        String mode = env("APP_MODE", "caller");
        switch (mode) {
            case "origin" -> OriginApp.run();
            case "caller" -> CallerApp.run();
            default -> throw new IllegalArgumentException("Unknown APP_MODE: " + mode);
        }
    }

    static String env(String key, String def) {
        String v = System.getenv(key);
        return (v == null || v.isBlank()) ? def : v;
    }
}
