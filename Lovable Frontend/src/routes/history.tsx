import { createFileRoute } from "@tanstack/react-router";
import { HistoryPage } from "@/components/mp/pages/HistoryPage";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "Trade History — Mirror Pupil" },
      { name: "description", content: "Completed trades with Lagos-time timestamps and CSV export." },
    ],
  }),
  component: HistoryPage,
});