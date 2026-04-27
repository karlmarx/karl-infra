"use client";

import type { ParsedDoc, Section } from "@/lib/types";
import { StorageProvider } from "@/lib/storage";
import { useMemo, useState } from "react";
import { QuestionCard } from "./QuestionCard";
import { ChecklistItemCard } from "./ChecklistItemCard";
import { ProgressBar } from "./ProgressBar";
import { SearchBar } from "./SearchBar";
import { SectionNav } from "./SectionNav";
import { SettingsDrawer } from "./SettingsDrawer";
import { Footer } from "./Footer";

interface Props {
  doc: ParsedDoc;
}

function contains(text: string | undefined, q: string): boolean {
  if (!text) return false;
  return text.toLowerCase().includes(q);
}

export function HomeView({ doc }: Props) {
  const [query, setQuery] = useState("");
  const [priorityOnly, setPriorityOnly] = useState(false);
  const q = query.trim().toLowerCase();

  const visibleSections = useMemo<Section[]>(() => {
    const out: Section[] = [];
    for (const s of doc.sections) {
      if (s.content.kind === "questions") {
        let questions = s.content.questions;
        if (priorityOnly) questions = questions.filter((qq) => qq.priority);
        if (q) {
          questions = questions.filter(
            (qq) =>
              contains(qq.text, q) ||
              contains(qq.topic, q) ||
              contains(qq.rationale, q),
          );
        }
        if (questions.length === 0) continue;
        out.push({ ...s, content: { kind: "questions", questions } });
      } else if (s.content.kind === "checklist") {
        if (priorityOnly) continue;
        let items = s.content.items;
        if (q) {
          items = items.filter(
            (it) => contains(it.title, q) || contains(it.body, q),
          );
        }
        if (items.length === 0) continue;
        out.push({ ...s, content: { kind: "checklist", items } });
      } else {
        if (priorityOnly || q) continue;
        out.push(s);
      }
    }
    return out;
  }, [doc, q, priorityOnly]);

  const totalQuestions = useMemo(
    () =>
      doc.sections.reduce(
        (n, s) =>
          n + (s.content.kind === "questions" ? s.content.questions.length : 0),
        0,
      ),
    [doc],
  );

  return (
    <StorageProvider>
      <div className="flex flex-col min-h-svh">
        <header className="sticky top-0 z-20 bg-bg/95 backdrop-blur border-b border-rule no-print">
          <div className="mx-auto w-full max-w-6xl px-4 lg:px-8 py-2.5 flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <a
                href="/"
                className="font-semibold text-ink leading-tight text-sm sm:text-base"
              >
                orthoappt
              </a>
              <div className="flex-1 min-w-0">
                <ProgressBar doc={doc} />
              </div>
              <SettingsDrawer />
            </div>
            <div className="flex items-center gap-2">
              <SearchBar value={query} onChange={setQuery} />
              <button
                type="button"
                onClick={() => setPriorityOnly((v) => !v)}
                aria-pressed={priorityOnly}
                className={`shrink-0 inline-flex items-center gap-1 rounded-md px-2.5 py-2 text-sm border transition-colors ${
                  priorityOnly
                    ? "bg-priority text-white border-priority"
                    : "border-rule text-ink-muted hover:text-ink"
                }`}
                title="Show only priority questions"
              >
                <span aria-hidden="true">★</span>
                <span className="hidden sm:inline">priority</span>
              </button>
            </div>
          </div>
        </header>

        <div className="mx-auto w-full max-w-6xl px-4 lg:px-8 py-6 flex-1 lg:grid lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-10">
          <SectionNav sections={visibleSections} />
          <main className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-semibold text-ink leading-tight">
              {doc.title}
            </h1>
            {doc.intro.length > 0 && !q && !priorityOnly && (
              <div className="mt-3 space-y-3 text-ink-muted text-sm sm:text-[0.9375rem] leading-relaxed">
                {doc.intro.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            )}

            <div className="mt-2 text-xs text-ink-faint">
              {totalQuestions} questions across {doc.sections.length} sections
              {priorityOnly && " · ★ filtered"}
              {q && ` · "${query}"`}
            </div>

            {visibleSections.map((s) => (
              <section
                key={s.id}
                id={s.id}
                className="mt-10 scroll-mt-32"
              >
                <h2 className="text-lg sm:text-xl font-semibold text-ink leading-snug">
                  {s.title}
                </h2>
                {s.lead && (
                  <p className="mt-2 text-sm text-ink-muted leading-relaxed">
                    {s.lead}
                  </p>
                )}
                <div className="mt-4 flex flex-col gap-3">
                  {s.content.kind === "questions" &&
                    s.content.questions.map((qq) => (
                      <QuestionCard key={qq.id} question={qq} />
                    ))}
                  {s.content.kind === "checklist" &&
                    s.content.items.map((it) => (
                      <ChecklistItemCard key={it.id} item={it} />
                    ))}
                  {s.content.kind === "prose" &&
                    s.content.paragraphs.map((p, i) => (
                      <p
                        key={i}
                        className="text-ink-muted text-sm sm:text-base leading-relaxed"
                      >
                        {p}
                      </p>
                    ))}
                </div>
              </section>
            ))}

            {visibleSections.length === 0 && (
              <p className="mt-12 text-center text-ink-muted">
                No questions match{q ? ` "${query}"` : ""}.
              </p>
            )}

            <Footer builtAt={doc.builtAt} />
          </main>
        </div>
      </div>
    </StorageProvider>
  );
}
