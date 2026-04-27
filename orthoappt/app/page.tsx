import { parseAppointmentDoc } from "@/lib/parseMarkdown";
import { HomeView } from "@/components/HomeView";
import path from "node:path";

export const dynamic = "force-static";

export default function Page() {
  const doc = parseAppointmentDoc(
    path.join(process.cwd(), "content", "appointment-questions.md"),
  );
  return <HomeView doc={doc} />;
}
