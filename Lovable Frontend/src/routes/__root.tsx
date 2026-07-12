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
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/mp/AppShell";
import { ConfirmProvider } from "@/components/mp/ConfirmDialog";
import { AuthProvider, useAuth } from "@/lib/mp/auth-context";
import { getSession } from "@/lib/mp/auth";
import { auth } from "@/lib/firebase";

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
      { rel: "icon", type: "image/png", href: "/favicon.png" },
      { rel: "apple-touch-icon", href: "/favicon.png" },
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
          <PendingApprovalGate isAuthRoute={isAuthRoute}>
            {isAuthRoute ? (
              <Outlet />
            ) : (
              <AppShell>
                <Outlet />
              </AppShell>
            )}
          </PendingApprovalGate>
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

// Component to show pending approval screen
function PendingApprovalGate({ children, isAuthRoute }: { children: ReactNode; isAuthRoute: boolean }) {
  const { user, loading, isApproved } = useAuth();
  
  // Don't interfere with auth routes
  if (isAuthRoute) return <>{children}</>;
  
  // Still loading
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }
  
  // User is logged in but not approved
  if (user && !isApproved) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500/10">
            <svg
              className="h-8 w-8 text-yellow-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-foreground">Account Pending Approval</h1>
          <p className="mt-4 text-muted-foreground">
            Your account has been created successfully, but it requires administrator approval before you can access the system.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Email: <span className="font-medium text-foreground">{user.email}</span>
          </p>
          <p className="mt-6 text-sm text-muted-foreground">
            You'll receive an email once your account is approved. Please contact your administrator if you have any questions.
          </p>
          <button
            onClick={() => auth.signOut()}
            className="mt-8 inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }
  
  // User is approved or not logged in
  return <>{children}</>;
}
