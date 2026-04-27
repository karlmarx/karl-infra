import { parseAppointmentDoc } from "@/lib/parseMarkdown";
import type { Question, Section } from "@/lib/types";
import path from "node:path";
import Link from "next/link";

export const dynamic = "force-static";

export const metadata = {
  title: "orthoappt — for Dr. Almodovar",
};

interface PriorityRow {
  question: Question;
  sectionTitle: string;
}

export default function DoctorPage() {
  const doc = parseAppointmentDoc(
    path.join(process.cwd(), "content", "appointment-questions.md"),
  );

  const priority: PriorityRow[] = [];
  for (const s of doc.sections) {
    if (s.content.kind !== "questions") continue;
    for (const q of s.content.questions) {
      if (q.priority) priority.push({ question: q, sectionTitle: s.title });
    }
  }

  const renderQuestion = (q: Question, opts: { showPriority: boolean }) => (
    <div
      key={q.id}
      className={`question-card mt-4 ${
        opts.showPriority && q.priority ? "border-l-4 border-l-priority pl-4" : "pl-0"
      }`}
    >
      {q.topic && (
        <div className="text-[0.85rem] uppercase tracking-wide font-semibold text-ink-muted">
          {q.topic}
        </div>
      )}
      <p
        className={`mt-1 leading-snug text-ink ${
          q.priority ? "text-[1.25rem] font-semibold" : "text-[1.15rem] font-medium"
        }`}
      >
        {opts.showPriority && q.priority ? <span className="text-priority mr-1">★</span> : null}
        {q.text}
      </p>
      {q.rationale && (
        <p className="mt-1 text-[0.95rem] text-ink-muted leading-relaxed">
          {q.rationale}
        </p>
      )}
    </div>
  );

  const renderSection = (s: Section) => {
    if (s.content.kind === "prose") return null;
    if (s.content.kind === "checklist") {
      return (
        <section
          key={s.id}
          className="mt-10 page-break"
        >
          <h2 className="text-[1.4rem] font-semibold text-ink leading-snug border-b border-rule pb-1.5">
            {s.title}
          </h2>
          {s.lead && <p className="mt-2 text-ink-muted">{s.lead}</p>}
          <ul className="mt-3 space-y-1.5 list-disc pl-6 text-[1.05rem]">
            {s.content.items.map((it) => (
              <li key={it.id}>
                {it.title && <span className="font-semibold">{it.title}</span>}
                {it.title ? " — " : ""}
                <span className="text-ink-muted">{it.body}</span>
              </li>
            ))}
          </ul>
        </section>
      );
    }
    return (
      <section key={s.id} className="mt-10 page-break">
        <h2 className="text-[1.4rem] font-semibold text-ink leading-snug border-b border-rule pb-1.5">
          {s.title}
        </h2>
        {s.lead && <p className="mt-2 text-ink-muted">{s.lead}</p>}
        {s.content.questions.map((q) => renderQuestion(q, { showPriority: true }))}
      </section>
    );
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-8 sm:py-10">
      <header className="no-print flex items-center justify-between mb-6">
        <Link href="/" className="text-sm text-ink-muted hover:text-ink">
          ← back
        </Link>
        <span className="text-xs text-ink-faint">
          For Dr. Almodovar · Print: ⌘P
        </span>
      </header>

      <h1 className="text-2xl sm:text-3xl font-bold text-ink leading-tight">
        Karl Marx — follow-up questions
      </h1>
      <p className="mt-1 text-ink-muted">
        Tuesday April 28, 2026 · Dr. Almodovar
      </p>
      <p className="mt-2 text-sm text-ink-muted">
        ★ items below are highest priority. Travel begins April 29 (Orlando, 5
        days).
      </p>

      {priority.length > 0 && (
        <section className="mt-8">
          <h2 className="text-[1.4rem] font-semibold text-ink leading-snug border-b border-rule pb-1.5">
            ★ Priority
          </h2>
          <p className="mt-2 text-sm text-ink-muted">
            If we run short on time, please answer these first.
          </p>
          {priority.map(({ question }) =>
            renderQuestion(question, { showPriority: false }),
          )}
        </section>
      )}

      {doc.sections.map(renderSection)}

      <footer className="mt-12 pt-4 border-t border-rule text-xs text-ink-faint">
        Printable handoff · {doc.sections.length} sections ·{" "}
        {priority.length} priority items
      </footer>
    </div>
  );
}
