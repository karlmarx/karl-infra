"use client";

import type { ParsedDoc, Question, Section } from "@/lib/types";
import {
  readStorageRaw,
  type ChecklistStateMap,
  type QuestionStateMap,
} from "@/lib/storage";
import Link from "next/link";
import { useEffect, useState } from "react";

interface Props {
  doc: ParsedDoc;
}

export function ExportView({ doc }: Props) {
  const [data, setData] = useState<{
    questions: QuestionStateMap;
    checklist: ChecklistStateMap;
  } | null>(null);

  useEffect(() => {
    setData(readStorageRaw());
  }, []);

  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-10 text-ink-muted">
        Loading saved answers…
      </div>
    );
  }

  const askedCount = Object.values(data.questions).filter((q) => q.asked).length;
  const followUpCount = Object.values(data.questions).filter((q) => q.followUp).length;
  const totalQ = doc.sections.reduce(
    (n, s) =>
      n + (s.content.kind === "questions" ? s.content.questions.length : 0),
    0,
  );

  const renderQ = (q: Question) => {
    const st = data.questions[q.id];
    const asked = st?.asked ?? false;
    const ans = (st?.answer ?? "").trim();
    const followUp = st?.followUp ?? false;
    return (
      <div
        key={q.id}
        className={`question-card mt-4 pl-3 ${
          q.priority ? "border-l-4 border-l-priority" : "border-l border-l-rule"
        }`}
      >
        {q.topic && (
          <div className="text-xs uppercase tracking-wide font-semibold text-ink-muted">
            {q.topic}
          </div>
        )}
        <p className={`mt-0.5 ${q.priority ? "font-semibold" : "font-medium"}`}>
          {q.priority && <span className="text-priority mr-1">★</span>}
          {q.text}
        </p>
        <div className="mt-1.5 text-sm">
          <span className="font-medium">Asked:</span>{" "}
          <span className={asked ? "text-ink" : "text-ink-faint"}>
            {asked ? "yes" : "no"}
          </span>
          {followUp && (
            <span className="ml-3 text-warn">· follow-up needed</span>
          )}
        </div>
        {ans ? (
          <div className="mt-1.5 whitespace-pre-wrap text-[0.95rem] leading-relaxed bg-rule/50 px-3 py-2 rounded">
            <span className="font-medium text-ink">Answer:</span> {ans}
          </div>
        ) : (
          <div className="mt-1.5 text-sm text-ink-faint italic">
            (no answer recorded)
          </div>
        )}
      </div>
    );
  };

  const renderSection = (s: Section) => {
    if (s.content.kind === "prose") return null;
    if (s.content.kind === "checklist") {
      return (
        <section key={s.id} className="mt-8">
          <h2 className="text-lg font-semibold border-b border-rule pb-1">
            {s.title}
          </h2>
          <ul className="mt-2.5 space-y-1.5 list-none pl-0 text-[0.95rem]">
            {s.content.items.map((it) => {
              const checked = data.checklist[it.id] ?? false;
              return (
                <li key={it.id} className="flex gap-2">
                  <span aria-hidden="true">{checked ? "☑" : "☐"}</span>
                  <span>
                    {it.title && <span className="font-medium">{it.title}</span>}
                    {it.title ? " — " : ""}
                    <span className="text-ink-muted">{it.body}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      );
    }
    return (
      <section key={s.id} className="mt-8">
        <h2 className="text-lg font-semibold border-b border-rule pb-1">
          {s.title}
        </h2>
        {s.content.questions.map(renderQ)}
      </section>
    );
  };

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 sm:py-10">
      <header className="no-print flex items-center justify-between mb-6">
        <Link href="/" className="text-sm text-ink-muted hover:text-ink">
          ← back
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-md bg-accent text-white px-3 py-1.5 text-sm font-medium"
        >
          Print / Save as PDF
        </button>
      </header>

      <h1 className="text-2xl sm:text-3xl font-bold leading-tight">
        Appointment notes
      </h1>
      <p className="mt-1 text-ink-muted">
        Tuesday April 28, 2026 · Dr. Almodovar
      </p>
      <div className="mt-3 text-sm text-ink-muted">
        {askedCount} of {totalQ} asked
        {followUpCount > 0 && ` · ${followUpCount} flagged for follow-up`}
      </div>

      {doc.sections.map(renderSection)}

      <footer className="mt-12 pt-4 border-t border-rule text-xs text-ink-faint">
        Generated{" "}
        {new Date().toLocaleString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })}
      </footer>
    </div>
  );
}
