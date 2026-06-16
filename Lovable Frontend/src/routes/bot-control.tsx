import { createFileRoute } from "@tanstack/react-router";
import { BotControlPage } from "@/components/mp/pages/BotControlPage";

export const Route = createFileRoute("/bot-control")({
  component: BotControlPage,
});