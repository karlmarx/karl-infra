// Run with: node --experimental-strip-types tools/inspect.mjs
// or:       npx tsx tools/inspect.mjs
import { parseAppointmentDoc, summarize } from "../lib/parseMarkdown.ts";
import * as path from "node:path";
import * as url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const md = path.resolve(__dirname, "..", "content", "appointment-questions.md");

const doc = parseAppointmentDoc(md);
const s = summarize(doc);

console.log("=".repeat(72));
console.log("TITLE:", s.title);
console.log("TOTAL QUESTIONS:", s.totalQ, " | ★ PRIORITY:", s.priorityQ);
console.log("INTRO PARAGRAPHS:", doc.intro.length);
console.log("=".repeat(72));
console.log();

for (const section of doc.sections) {
  console.log("##", section.title, "  [" + section.content.kind + "]");
  if (section.lead) console.log("  lead:", section.lead.slice(0, 110) + (section.lead.length > 110 ? "…" : ""));
  if (section.content.kind === "questions") {
    section.content.questions.forEach((q, i) => {
      const star = q.priority ? "★ " : "  ";
      const topicTag = q.topic ? ` [${q.topic.slice(0, 60)}${q.topic.length > 60 ? "…" : ""}]` : "";
      console.log(`  ${star}${i + 1}.${topicTag}`);
      console.log(`     Q: ${q.text.slice(0, 140)}${q.text.length > 140 ? "…" : ""}`);
      if (q.rationale) {
        console.log(`     R: ${q.rationale.slice(0, 100)}${q.rationale.length > 100 ? "…" : ""}`);
      } else {
        console.log("     R: (none)");
      }
    });
  } else if (section.content.kind === "checklist") {
    section.content.items.forEach((it, i) => {
      console.log(`  □ ${i + 1}. ${it.title ?? ""}`);
      console.log(`     ${it.body.slice(0, 110)}${it.body.length > 110 ? "…" : ""}`);
    });
  } else {
    section.content.paragraphs.forEach((p, i) => {
      console.log(`  ¶${i + 1} ${p.slice(0, 110)}${p.length > 110 ? "…" : ""}`);
    });
  }
  console.log();
}

console.log("=".repeat(72));
console.log("PER-SECTION SUMMARY:");
for (const c of s.sections) {
  console.log(" ", JSON.stringify(c));
}
