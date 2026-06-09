import { createFileRoute } from "@tanstack/react-router";
import { ActiveTradesPage } from "@/components/mp/pages/ActiveTradesPage";

export const Route = createFileRoute("/trades")({
  head: () => ({
    meta: [
      { title: "Active Trades — Mirror Pupil" },
      { name: "description", content: "Manage open positions: close, breakeven, partial profit." },
    ],
  }),
  component: ActiveTradesPage,
});