"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
} from "react";

const Q_KEY = "orthoappt:questions:v1";
const C_KEY = "orthoappt:checklist:v1";

export interface QState {
  asked: boolean;
  answer: string;
  followUp: boolean;
}

export type QuestionStateMap = Record<string, QState>;
export type ChecklistStateMap = Record<string, boolean>;

interface State {
  hydrated: boolean;
  questions: QuestionStateMap;
  checklist: ChecklistStateMap;
}

type Action =
  | { type: "hydrate"; questions: QuestionStateMap; checklist: ChecklistStateMap }
  | { type: "patchQuestion"; id: string; patch: Partial<QState> }
  | { type: "setChecklist"; id: string; checked: boolean }
  | { type: "reset" };

const DEFAULT_Q: QState = { asked: false, answer: "", followUp: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "hydrate":
      return { hydrated: true, questions: action.questions, checklist: action.checklist };
    case "patchQuestion": {
      const prev = state.questions[action.id] ?? DEFAULT_Q;
      const next = { ...prev, ...action.patch };
      return { ...state, questions: { ...state.questions, [action.id]: next } };
    }
    case "setChecklist":
      return {
        ...state,
        checklist: { ...state.checklist, [action.id]: action.checked },
      };
    case "reset":
      return { ...state, questions: {}, checklist: {} };
  }
}

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

interface Ctx {
  hydrated: boolean;
  getQuestion: (id: string) => QState;
  patchQuestion: (id: string, patch: Partial<QState>) => void;
  isChecked: (id: string) => boolean;
  setChecked: (id: string, checked: boolean) => void;
  reset: () => void;
  questionMap: QuestionStateMap;
}

const StorageContext = createContext<Ctx | null>(null);

export function StorageProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, dispatch] = useReducer(reducer, {
    hydrated: false,
    questions: {},
    checklist: {},
  });
  const writeTimer = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    dispatch({
      type: "hydrate",
      questions: safeParse<QuestionStateMap>(localStorage.getItem(Q_KEY), {}),
      checklist: safeParse<ChecklistStateMap>(localStorage.getItem(C_KEY), {}),
    });
  }, []);

  useEffect(() => {
    if (!state.hydrated || typeof window === "undefined") return;
    if (writeTimer.current) window.clearTimeout(writeTimer.current);
    writeTimer.current = window.setTimeout(() => {
      try {
        localStorage.setItem(Q_KEY, JSON.stringify(state.questions));
        localStorage.setItem(C_KEY, JSON.stringify(state.checklist));
      } catch {
        // quota / private mode — silent fail
      }
    }, 150);
    return () => {
      if (writeTimer.current) window.clearTimeout(writeTimer.current);
    };
  }, [state]);

  const getQuestion = useCallback(
    (id: string) => state.questions[id] ?? DEFAULT_Q,
    [state.questions],
  );
  const patchQuestion = useCallback(
    (id: string, patch: Partial<QState>) => dispatch({ type: "patchQuestion", id, patch }),
    [],
  );
  const isChecked = useCallback(
    (id: string) => Boolean(state.checklist[id]),
    [state.checklist],
  );
  const setChecked = useCallback(
    (id: string, checked: boolean) => dispatch({ type: "setChecklist", id, checked }),
    [],
  );
  const reset = useCallback(() => dispatch({ type: "reset" }), []);

  const value = useMemo<Ctx>(
    () => ({
      hydrated: state.hydrated,
      getQuestion,
      patchQuestion,
      isChecked,
      setChecked,
      reset,
      questionMap: state.questions,
    }),
    [state.hydrated, state.questions, getQuestion, patchQuestion, isChecked, setChecked, reset],
  );

  return <StorageContext.Provider value={value}>{children}</StorageContext.Provider>;
}

export function useStorage(): Ctx {
  const ctx = useContext(StorageContext);
  if (!ctx) throw new Error("useStorage must be used within StorageProvider");
  return ctx;
}

export function readStorageRaw(): {
  questions: QuestionStateMap;
  checklist: ChecklistStateMap;
} {
  if (typeof window === "undefined") return { questions: {}, checklist: {} };
  return {
    questions: safeParse<QuestionStateMap>(localStorage.getItem(Q_KEY), {}),
    checklist: safeParse<ChecklistStateMap>(localStorage.getItem(C_KEY), {}),
  };
}
