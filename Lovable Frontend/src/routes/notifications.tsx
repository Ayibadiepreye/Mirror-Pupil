import { createFileRoute } from "@tanstack/react-router";
import { NotificationsPage } from "@/components/mp/pages/NotificationsPage";

export const Route = createFileRoute("/notifications")({
  head: () => ({
    meta: [
      { title: "Notifications — Mirror Pupil" },
      { name: "description", content: "System alerts, signal events, breaches and executions." },
    ],
  }),
  component: NotificationsPage,
});