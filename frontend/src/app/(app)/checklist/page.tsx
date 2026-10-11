import type { Metadata } from "next";

import { ChecklistView } from "./checklist-view";

export const metadata: Metadata = { title: "Security checklist" };

export default function ChecklistPage() {
  return <ChecklistView />;
}
