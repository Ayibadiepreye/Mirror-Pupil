import { createFileRoute } from "@tanstack/react-router";
import { AccountsPage } from "@/components/mp/pages/AccountsPage";

export const Route = createFileRoute("/accounts")({
  head: () => ({
    meta: [
      { title: "Accounts — Mirror Pupil" },
      { name: "description", content: "Manage TradeLocker accounts, pause/resume, and assign risk profiles." },
    ],
  }),
  component: AccountsPage,
});