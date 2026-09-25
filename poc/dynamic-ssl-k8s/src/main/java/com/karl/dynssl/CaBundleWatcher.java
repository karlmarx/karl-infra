package com.karl.dynssl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.FileSystems;
import java.nio.file.Path;
import java.nio.file.WatchKey;
import java.nio.file.WatchService;

import static java.nio.file.StandardWatchEventKinds.ENTRY_CREATE;
import static java.nio.file.StandardWatchEventKinds.ENTRY_DELETE;
import static java.nio.file.StandardWatchEventKinds.ENTRY_MODIFY;

/**
 * Watches the CA-bundle MOUNT DIRECTORY (not the file) and fires {@code onChange} when
 * Kubernetes atomically repoints the {@code ..data} symlink on a ConfigMap update.
 *
 * Why watch the directory and react to {@code ..data}:
 * a ConfigMap volume is a tree of symlinks — the visible {@code ca-bundle.pem} points at
 * {@code ..data/ca-bundle.pem}, and {@code ..data} points at a timestamped dir. On update
 * the kubelet writes a NEW timestamped dir and re-points {@code ..data}; the per-file
 * symlink is never touched. inotify on the file alone goes deaf after one event, so we
 * watch the directory and key off the {@code ..data} ENTRY_CREATE, re-registering the
 * watch if it is ever invalidated.
 */
public final class CaBundleWatcher implements Runnable {

    private static final Logger log = LoggerFactory.getLogger(CaBundleWatcher.class);

    private final Path dir;
    private final Runnable onChange;

    public CaBundleWatcher(Path mountDir, Runnable onChange) {
        this.dir = mountDir;
        this.onChange = onChange;
    }

    @Override
    public void run() {
        log.info("Watching CA bundle directory {} for ..data symlink swaps", dir);
        try (WatchService ws = FileSystems.getDefault().newWatchService()) {
            dir.register(ws, ENTRY_CREATE, ENTRY_MODIFY, ENTRY_DELETE);
            while (!Thread.currentThread().isInterrupted()) {
                WatchKey key = ws.take();
                boolean dataSwapped = key.pollEvents().stream().anyMatch(e -> {
                    Object ctx = e.context();
                    return ctx != null && ctx.toString().equals("..data");
                });
                if (dataSwapped) {
                    log.info("Detected ConfigMap update (..data symlink swap) — reloading trust");
                    try {
                        onChange.run();
                    } catch (Exception ex) {
                        // Keep watching and keep the OLD trust material on a bad bundle.
                        log.error("Trust reload failed; keeping previous trust material", ex);
                    }
                }
                if (!key.reset()) {
                    log.warn("Watch key invalidated — re-registering watch on {}", dir);
                    dir.register(ws, ENTRY_CREATE, ENTRY_MODIFY, ENTRY_DELETE);
                }
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            log.error("CA bundle watcher stopped unexpectedly", e);
        }
    }
}
