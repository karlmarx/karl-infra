"use client";

import { useStorage } from "@/lib/storage";
import { useEffect, useState } from "react";

export function SettingsDrawer() {
  const { reset } = useStorage();
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        setConfirm(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const doReset = () => {
    reset();
    setConfirm(false);
    setOpen(false);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Settings"
        className="h-9 w-9 grid place-items-center rounded-md text-ink-muted hover:text-ink hover:bg-rule no-print"
        title="Settings"
      >
        ⚙
      </button>
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Settings"
          className="fixed inset-0 z-50 bg-black/40 no-print grid place-items-center p-4"
          onClick={() => {
            setOpen(false);
            setConfirm(false);
          }}
        >
          <div
            className="w-full max-w-sm bg-surface rounded-xl p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Settings</h2>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setConfirm(false);
                }}
                aria-label="Close"
                className="h-8 w-8 grid place-items-center text-ink-muted"
              >
                ✕
              </button>
            </div>
            <div className="text-sm text-ink-muted mb-3">
              Reset all asked-status, answers, and follow-up flags. Use this to
              do a dry run before Tuesday.
            </div>
            {!confirm ? (
              <button
                type="button"
                onClick={() => setConfirm(true)}
                className="w-full rounded-md border border-rule px-3 py-2 text-sm text-ink hover:bg-rule"
              >
                Reset all answers…
              </button>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="text-sm text-warn font-medium">
                  This clears every answer and check. Cannot be undone.
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={doReset}
                    className="flex-1 rounded-md bg-warn text-white px-3 py-2 text-sm font-medium"
                    style={{ background: "var(--color-warn)" }}
                  >
                    Yes, reset
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirm(false)}
                    className="flex-1 rounded-md border border-rule px-3 py-2 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
            <div className="mt-4 text-xs text-ink-faint">
              <a href="/doctor" className="underline">
                Doctor view
              </a>{" "}
              ·{" "}
              <a href="/export" className="underline">
                Export
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
