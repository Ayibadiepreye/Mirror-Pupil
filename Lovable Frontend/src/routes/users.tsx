import { createFileRoute } from "@tanstack/react-router";
import { UsersPage } from "@/components/mp/pages/UsersPage";

export const Route = createFileRoute("/users")({
  head: () => ({
    meta: [
      { title: "User Management — Mirror Pupil" },
      { name: "description", content: "Approve and manage users." },
    ],
  }),
  component: UsersPage,
});
