import { createFileRoute } from "@tanstack/react-router";
import { BotControlPage } from "@/components/mp/pages/BotControlPage";

export const Route = createFileRoute("/bot-control")({
  head: () => ({
    meta: [
      { title: "Bot Control — Mirror Pupil" },
      { name: "description", content: "Operate the Mirror Pupil bot and run emergency actions." },
    ],
  }),
  component: BotControlPage,
});