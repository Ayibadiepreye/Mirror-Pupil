import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "@/components/mp/pages/LoginPage";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — Mirror Pupil" },
      { name: "description", content: "Sign in to Mirror Pupil with Google or email." },
    ],
  }),
  component: LoginPage,
});
