"use client";

import { useStorage } from "@/lib/storage";
import type { Question } from "@/lib/types";
import { useEffect, useRef, useState } from "react";

interface Props {
  question: Question;
}

export function QuestionCard({ question }: Props) {
  const { hydrated, getQuestion, patchQuestion } = useStorage();
  const state = getQuestion(question.id);

  const [draft, setDraft] = useState(state.answer);
  const lastSaved = useRef(state.answer);

  useEffect(() => {
    if (state.answer !== lastSaved.current && state.answer !== draft) {
      setDraft(state.answer);
      lastSaved.current = state.answer;
    }
  }, [state.answer, draft]);

  const commitAnswer = () => {
    if (draft === lastSaved.current) return;
    patchQuestion(question.id, { answer: draft });
    lastSaved.current = draft;
  };

  const isDimmed = hydrated && state.asked && !state.followUp;

  return (
    <article
      id={question.id}
      data-priority={question.priority || undefined}
      data-asked={state.asked || undefined}
      className={`question-card relative rounded-lg border bg-surface px-4 py-4 sm:px-5 sm:py-5 transition-opacity scroll-mt-32 ${
        question.priority
          ? "border-rule border-l-4 border-l-priority"
          : "border-rule"
      } ${isDimmed ? "opacity-60" : ""}`}
    >
      {question.topic && (
        <div className="text-xs font-medium uppercase tracking-wide text-ink-muted mb-1.5">
          {question.priority && (
            <span aria-label="priority" className="text-priority mr-1">
              ★
            </span>
          )}
          {question.topic}
        </div>
      )}
      {!question.topic && question.priority && (
        <div className="text-xs font-medium uppercase tracking-wide text-priority mb-1.5">
          ★ priority
        </div>
      )}
      <h3
        className={`question-text text-ink ${
          question.priority ? "font-semibold" : "font-medium"
        }`}
      >
        {question.text}
      </h3>

      {question.rationale && (
        <details className="mt-2.5">
          <summary className="inline-flex items-center gap-1 text-sm text-ink-muted hover:text-ink">
            <span className="disclosure-caret inline-block transition-transform">
              ›
            </span>
            why this question?
          </summary>
          <div className="mt-2 text-sm text-ink-muted leading-relaxed">
            {question.rationale}
          </div>
        </details>
      )}

      <div className="mt-4 flex flex-col gap-3 no-print">
        <label className="flex items-center gap-3 cursor-pointer min-h-11 select-none">
          <input
            type="checkbox"
            checked={state.asked}
            disabled={!hydrated}
            onChange={(e) =>
              patchQuestion(question.id, { asked: e.target.checked })
            }
            className="h-5 w-5 accent-accent"
          />
          <span className="text-base text-ink">Asked</span>
        </label>

        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitAnswer}
          disabled={!hydrated}
          placeholder="Doctor's answer…"
          rows={2}
          className="w-full resize-y rounded border border-rule bg-bg px-3 py-2 text-base focus:border-accent focus:bg-surface min-h-20"
        />

        <label className="flex items-center gap-3 cursor-pointer min-h-11 select-none">
          <input
            type="checkbox"
            checked={state.followUp}
            disabled={!hydrated}
            onChange={(e) =>
              patchQuestion(question.id, { followUp: e.target.checked })
            }
            className="h-5 w-5 accent-warn"
          />
          <span className="text-sm text-ink-muted">Follow up needed</span>
        </label>
      </div>

      <div className="print-only mt-3 text-sm">
        <div>
          <strong>Asked:</strong> {state.asked ? "✓" : "☐"}
          {state.followUp && "  ·  follow up needed"}
        </div>
        {state.answer && (
          <div className="mt-1.5 whitespace-pre-wrap">
            <strong>Answer:</strong> {state.answer}
          </div>
        )}
      </div>
    </article>
  );
}
