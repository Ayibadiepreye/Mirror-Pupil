import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard, Users, TrendingUp, History, Settings, Bot, Bell,
  Circle, Plus, X, LogOut,
} from "lucide-react";
import { notificationsApi, QK, botApi } from "@/lib/mp/api";
import { useMirrorPupilWebSocket } from "@/lib/mp/ws";
import { cn } from "@/lib/utils";
import { useEffect, useRef, useState, type ReactNode } from "react";
import logoUrl from "@/assets/logo.svg";
import { clearSession } from "@/lib/mp/auth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Accounts", icon: Users },
  { to: "/trades", label: "Active", icon: TrendingUp },
  { to: "/history", label: "History", icon: History },
  { to: "/bot-control", label: "Bot", icon: Bot },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

function StatusDot({ status }: { status: ReturnType<typeof useMirrorPupilWebSocket> }) {
  const color =
    status === "connected" ? "text-[color:var(--mp-success)]"
    : status === "offline" ? "text-[color:var(--mp-warning)]"
    : status === "connecting" ? "text-[color:var(--mp-info)]"
    : "text-[color:var(--mp-danger)]";
  const label =
    status === "connected" ? "Live"
    : status === "offline" ? "Mock"
    : status === "connecting" ? "…"
    : "Off";
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", color)}>
      <Circle className="size-2 fill-current" aria-hidden />
      {label}
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const wsStatus = useMirrorPupilWebSocket();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();

  const unreadQ = useQuery({
    queryKey: QK.notifications(true),
    queryFn: () => notificationsApi.list({ unread_only: true, limit: 100 }),
    refetchInterval: 15_000,
  });
  const botQ = useQuery({
    queryKey: QK.botStatus,
    queryFn: botApi.status,
    refetchInterval: 10_000,
  });

  const unread = unreadQ.data?.length ?? 0;
  const botRunning = botQ.data?.status === "running";
  const onNotificationsPage = pathname.startsWith("/notifications");

  return (
    <div className="min-h-screen flex flex-col bg-[color:var(--mp-app)] text-[color:var(--mp-text)]">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-[color:var(--mp-border)] bg-[color:var(--mp-base)]/95 backdrop-blur">
        <div className="flex items-center justify-between px-4 md:px-6 h-14">
          <Link to="/" className="flex items-center gap-2.5">
            <img
              src={logoUrl}
              alt="Mirror Pupil logo"
              className="size-7 rounded-md shadow-sm shadow-[color:var(--mp-crimson)]/40"
            />
            <div className="leading-tight">
              <div className="font-semibold text-sm tracking-tight">Mirror Pupil</div>
              <div className="text-[10px] text-[color:var(--mp-text-dim)] uppercase tracking-widest">
                v5.1
              </div>
            </div>
          </Link>

          <div className="flex items-center gap-3 md:gap-5">
            <div className="hidden sm:flex items-center gap-2 text-xs">
              <span className={cn(
                "inline-flex items-center gap-1.5 px-2 py-1 rounded-full border",
                botRunning
                  ? "border-[color:var(--mp-success)]/40 bg-[color:var(--mp-success)]/10 text-[color:var(--mp-success)]"
                  : "border-[color:var(--mp-text-dim)]/30 bg-white/5 text-[color:var(--mp-text-dim)]"
              )}>
                <Bot className="size-3" />
                {botQ.data?.status ?? "…"}
              </span>
              <StatusDot status={wsStatus} />
            </div>
            <button
              type="button"
              onClick={() => navigate({ to: onNotificationsPage ? "/" : "/notifications" })}
              className={cn(
                "relative p-2 rounded-md transition-colors",
                onNotificationsPage
                  ? "bg-[color:var(--mp-red)]/15 text-[color:var(--mp-red)]"
                  : "hover:bg-white/5"
              )}
              aria-label={onNotificationsPage ? "Close notifications" : "Open notifications"}
              aria-pressed={onNotificationsPage}
            >
              <Bell className="size-5" />
              {unread > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 grid place-items-center rounded-full bg-[color:var(--mp-red)] text-white text-[10px] font-semibold">
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => { clearSession(); navigate({ to: "/login" }); }}
              className="p-2 rounded-md hover:bg-white/5 text-[color:var(--mp-text-dim)] hover:text-white transition-colors"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Sidebar (md+) */}
        <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-3 gap-1">
          {NAV.map((item) => {
            const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-gradient-to-r from-[color:var(--mp-crimson)]/30 to-transparent text-white border-l-2 border-[color:var(--mp-red)] pl-[10px]"
                    : "text-[color:var(--mp-text-dim)] hover:text-white hover:bg-white/5"
                )}
              >
                <Icon className="size-4" />
                {item.label}
              </Link>
            );
          })}
          <div className="mt-auto pt-4 border-t border-[color:var(--mp-border)] text-[10px] text-[color:var(--mp-text-dim)] uppercase tracking-wider px-2">
            Knights of the Blood Oath
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-[1600px] mx-auto p-4 md:p-6">{children}</div>
        </main>
      </div>

      {/* Floating action nav (mobile) */}
      <MobileFabNav pathname={pathname} />
    </div>
  );
}

function MobileFabNav({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Arrange items in a quarter-arc (180°→270°) around the FAB,
  // sweeping up-and-to-the-left from the bottom-right corner.
  const RADIUS = 110; // px from FAB center to each item center
  const items = NAV;
  const startDeg = 180; // straight left
  const endDeg = 270;   // straight up
  const step = items.length > 1 ? (endDeg - startDeg) / (items.length - 1) : 0;

  return (
    <div
      ref={ref}
      className="md:hidden fixed bottom-5 right-5 z-50"
      style={{ width: 56, height: 56 }}
    >
      {/* Radial items — absolutely positioned around the FAB center */}
      {items.map((item, i) => {
        const angle = (startDeg + step * i) * (Math.PI / 180);
        const dx = Math.cos(angle) * RADIUS;
        const dy = Math.sin(angle) * RADIUS;
        const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
        const Icon = item.icon;
        return (
          <Link
            key={item.to}
            to={item.to}
            aria-label={item.label}
            tabIndex={open ? 0 : -1}
            className={cn(
              "absolute top-1/2 left-1/2 -mt-6 -ml-6 size-12 rounded-full grid place-items-center",
              "border shadow-lg shadow-black/40 backdrop-blur",
              "transition-all duration-300 ease-out",
              active
                ? "bg-[color:var(--mp-red)] text-white border-[color:var(--mp-red)]"
                : "bg-[color:var(--mp-base)]/95 text-[color:var(--mp-text)] border-[color:var(--mp-border)]",
              open
                ? "opacity-100 scale-100 pointer-events-auto"
                : "opacity-0 scale-50 pointer-events-none"
            )}
            style={{
              transform: open
                ? `translate(${dx}px, ${dy}px)`
                : "translate(0,0)",
              transitionDelay: open ? `${i * 35}ms` : "0ms",
            }}
            title={item.label}
          >
            <Icon className="size-5" />
            <span className="sr-only">{item.label}</span>
          </Link>
        );
      })}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-expanded={open}
        className={cn(
          "absolute inset-0 size-14 rounded-full grid place-items-center text-white",
          "shadow-xl shadow-[color:var(--mp-red)]/40 transition-transform duration-200",
          "bg-gradient-to-br from-[color:var(--mp-crimson)] to-[color:var(--mp-red)]",
          "hover:scale-105 active:scale-95",
          open && "rotate-45"
        )}
      >
        {open ? <X className="size-6" /> : <Plus className="size-6" />}
      </button>
    </div>
  );
}