import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/components/mp/pages/SettingsPage";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Mirror Pupil" },
      { name: "description", content: "Configure channels, risk profiles and bot settings." },
    ],
  }),
  component: SettingsPage,
});