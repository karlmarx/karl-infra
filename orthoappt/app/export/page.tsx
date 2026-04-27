import { parseAppointmentDoc } from "@/lib/parseMarkdown";
import { ExportView } from "@/components/ExportView";
import path from "node:path";

export const dynamic = "force-static";

export const metadata = {
  title: "orthoappt — export",
};

export default function ExportPage() {
  const doc = parseAppointmentDoc(
    path.join(process.cwd(), "content", "appointment-questions.md"),
  );
  return <ExportView doc={doc} />;
}
