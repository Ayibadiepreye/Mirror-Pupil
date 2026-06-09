import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/components/mp/pages/DashboardPage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Mirror Pupil" },
      { name: "description", content: "Live overview of your prop accounts, active trades, and bot status." },
    ],
  }),
  component: DashboardPage,
});
