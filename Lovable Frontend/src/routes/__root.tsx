import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
  useRouterState,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/mp/AppShell";
import { ConfirmProvider } from "@/components/mp/ConfirmDialog";
import { AuthProvider } from "@/lib/mp/auth-context";
import { getSession } from "@/lib/mp/auth";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Mirror Pupil — Trading Bot Control" },
      { name: "description", content: "Mirror Pupil v5.1 — real-time prop-firm trading bot management." },
      { name: "author", content: "Mirror Pupil" },
      { property: "og:title", content: "Mirror Pupil — Trading Bot Control" },
      { property: "og:description", content: "Real-time prop-firm trading bot management." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const isAuthRoute = pathname === "/login";

  // Reactive session state — listens for the "mp:session" custom event
  // emitted by setSession/clearSession.
  const [authed, setAuthed] = useState<boolean>(() => !!getSession());
  useEffect(() => {
    const sync = () => setAuthed(!!getSession());
    window.addEventListener("mp:session", sync);
    window.addEventListener("storage", sync);
    sync();
    return () => {
      window.removeEventListener("mp:session", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Redirect unauthenticated users to /login (client-side gate).
  useEffect(() => {
    if (!authed && !isAuthRoute) navigate({ to: "/login" });
  }, [authed, isAuthRoute, navigate]);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ConfirmProvider>
          {isAuthRoute ? (
            <Outlet />
          ) : (
            <AppShell>
              <Outlet />
            </AppShell>
          )}
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              classNames: {
                toast: "bg-[color:var(--mp-base)] border-[color:var(--mp-border)] text-[color:var(--mp-text)]",
              },
            }}
          />
        </ConfirmProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
