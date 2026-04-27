export interface Question {
  id: string;
  topic?: string;
  text: string;
  priority: boolean;
  rationale?: string;
}

export interface ChecklistItem {
  id: string;
  title?: string;
  body: string;
}

export type SectionContent =
  | { kind: "questions"; questions: Question[] }
  | { kind: "checklist"; items: ChecklistItem[] }
  | { kind: "prose"; paragraphs: string[] };

export interface Section {
  id: string;
  title: string;
  lead?: string;
  content: SectionContent;
}

export interface ParsedDoc {
  title: string;
  intro: string[];
  sections: Section[];
  builtAt: string;
}
