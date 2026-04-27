import { unified } from "unified";
import remarkParse from "remark-parse";
import { toString } from "mdast-util-to-string";
import type {
  Heading,
  List,
  Paragraph,
  Root,
  RootContent,
  Strong,
} from "mdast";
import * as fs from "fs";
import type {
  ChecklistItem,
  ParsedDoc,
  Question,
  Section,
  SectionContent,
} from "./types";

export type {
  ChecklistItem,
  ParsedDoc,
  Question,
  Section,
  SectionContent,
} from "./types";

const QUOTE_OPEN = /^["“]/;
const QUOTE_CLOSE = /["”]$/;
const QUESTION_QUOTE = /["“]([^"”“]+)["”]/;

const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);

function findStrong(
  p: Paragraph,
): { strong: Strong; index: number } | null {
  for (let i = 0; i < p.children.length; i++) {
    if (p.children[i].type === "strong") {
      return { strong: p.children[i] as Strong, index: i };
    }
  }
  return null;
}

function restAsText(p: Paragraph, fromIndex: number): string {
  return p.children
    .slice(fromIndex)
    .map((c) => toString(c))
    .join("")
    .trim();
}

function cleanRationale(r: string): string {
  let out = r.trim();
  out = out.replace(/^["”\.]+/, "").trim();
  out = out.replace(/^Why it matters:\s*/i, "");
  out = out.replace(/^Worth asking\s*[—\-–:]?\s*/i, "");
  return out.trim();
}

function extractQuestion(
  p: Paragraph,
  sectionSlug: string,
  qIdx: number,
): Question | null {
  const sg = findStrong(p);
  if (!sg) return null;

  const boldRaw = toString(sg.strong).trim();
  let priority = false;
  let working = boldRaw;
  if (working.startsWith("★")) {
    priority = true;
    working = working.replace(/^★\s*/, "").trim();
  }

  let topic: string | undefined;
  let questionText: string | undefined;

  if (QUOTE_OPEN.test(working) && QUOTE_CLOSE.test(working)) {
    questionText = working.replace(QUOTE_OPEN, "").replace(QUOTE_CLOSE, "").trim();
  } else {
    topic = working;
    const rest = restAsText(p, sg.index + 1);
    const m = rest.match(QUESTION_QUOTE);
    if (m) questionText = m[1].trim();
  }

  if (!questionText || !questionText.includes("?")) return null;

  const full = toString(p);
  const at = full.indexOf(questionText);
  let rationale: string | undefined;
  if (at >= 0) {
    const r = cleanRationale(full.slice(at + questionText.length));
    if (r.length > 0) rationale = r;
  }

  return {
    id: `${sectionSlug}-q${qIdx + 1}`,
    topic,
    text: questionText,
    priority,
    rationale,
  };
}

function extractChecklist(
  list: List,
  sectionSlug: string,
  startIdx: number,
): ChecklistItem[] {
  const items: ChecklistItem[] = [];
  list.children.forEach((li, i) => {
    if (li.type !== "listItem") return;
    const first = li.children[0];
    if (!first || first.type !== "paragraph") return;
    const p = first as Paragraph;
    const sg = findStrong(p);
    let title: string | undefined;
    let body: string;
    if (sg) {
      title = toString(sg.strong).trim();
      body = restAsText(p, sg.index + 1)
        .replace(/^[\s—\-–:.]+/, "")
        .trim();
    } else {
      body = toString(p).trim();
    }
    items.push({
      id: `${sectionSlug}-c${startIdx + i + 1}`,
      title,
      body,
    });
  });
  return items;
}

export function parseAppointmentDoc(filePath: string): ParsedDoc {
  const md = fs.readFileSync(filePath, "utf8");
  const tree = unified().use(remarkParse).parse(md) as Root;

  let title = "Appointment Questions";
  const intro: string[] = [];
  const sections: Section[] = [];

  let current: {
    id: string;
    title: string;
    questions: Question[];
    checklist: ChecklistItem[];
    prose: string[];
    leadCandidate?: string;
  } | null = null;

  const closeSection = () => {
    if (!current) return;
    let content: SectionContent;
    if (current.questions.length > 0) {
      content = { kind: "questions", questions: current.questions };
    } else if (current.checklist.length > 0) {
      content = { kind: "checklist", items: current.checklist };
    } else if (current.prose.length > 0) {
      content = { kind: "prose", paragraphs: current.prose };
    } else {
      content = { kind: "prose", paragraphs: [] };
    }
    sections.push({
      id: current.id,
      title: current.title,
      lead: current.leadCandidate,
      content,
    });
    current = null;
  };

  for (const node of tree.children as RootContent[]) {
    if (node.type === "heading") {
      const h = node as Heading;
      if (h.depth === 1) {
        title = toString(h);
      } else if (h.depth === 2) {
        closeSection();
        const headingText = toString(h);
        current = {
          id: slugify(headingText),
          title: headingText,
          questions: [],
          checklist: [],
          prose: [],
        };
      }
      continue;
    }

    if (!current) {
      if (node.type === "paragraph") intro.push(toString(node));
      continue;
    }

    if (node.type === "paragraph") {
      const q = extractQuestion(
        node as Paragraph,
        current.id,
        current.questions.length,
      );
      if (q) {
        current.questions.push(q);
      } else {
        const text = toString(node).trim();
        if (
          current.questions.length === 0 &&
          current.checklist.length === 0 &&
          current.prose.length === 0 &&
          !current.leadCandidate &&
          text.length < 400
        ) {
          current.leadCandidate = text;
        } else {
          current.prose.push(text);
        }
      }
    } else if (node.type === "list") {
      const items = extractChecklist(
        node as List,
        current.id,
        current.checklist.length,
      );
      current.checklist.push(...items);
    }
  }
  closeSection();

  return {
    title,
    intro,
    sections,
    builtAt: new Date().toISOString(),
  };
}

export function summarize(doc: ParsedDoc) {
  const counts = doc.sections.map((s) => {
    if (s.content.kind === "questions") {
      const total = s.content.questions.length;
      const priority = s.content.questions.filter((q) => q.priority).length;
      return {
        section: s.title,
        kind: s.content.kind,
        questions: total,
        priority,
      };
    }
    if (s.content.kind === "checklist") {
      return {
        section: s.title,
        kind: s.content.kind,
        items: s.content.items.length,
      };
    }
    return {
      section: s.title,
      kind: s.content.kind,
      paragraphs: s.content.paragraphs.length,
    };
  });
  const totalQ = doc.sections.reduce(
    (n, s) => n + (s.content.kind === "questions" ? s.content.questions.length : 0),
    0,
  );
  const priorityQ = doc.sections.reduce(
    (n, s) =>
      n +
      (s.content.kind === "questions"
        ? s.content.questions.filter((q) => q.priority).length
        : 0),
    0,
  );
  return { title: doc.title, totalQ, priorityQ, sections: counts };
}
