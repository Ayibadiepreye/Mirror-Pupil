import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  Activity, AlertTriangle, Bot, CheckCheck, DollarSign, Info,
  PauseCircle, PlayCircle, ShieldOff, TrendingUp, Users, Zap,
} from "lucide-react";
import { accountsApi, botApi, notificationsApi, QK, tradesApi } from "@/lib/mp/api";
import {
  formatBalance, formatCurrency, formatTimeAgo, getPnLColor, shortenKey,
} from "@/lib/mp/utils";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

const CAT_ICON = {
  SIGNAL: Zap,
  EXECUTION: CheckCheck,
  MANAGEMENT: Info,
  BREACH: AlertTriangle,
  SYSTEM: Activity,
} as const;

function StatCard(props: {
  label: string; value: React.ReactNode; hint?: React.ReactNode;
  icon: React.ComponentType<{ className?: string }>; tone?: "default" | "good" | "bad" | "warn";
}) {
  const tone =
    props.tone === "good" ? "from-[color:var(--mp-success)]/30 to-transparent"
    : props.tone === "bad" ? "from-[color:var(--mp-danger)]/30 to-transparent"
    : props.tone === "warn" ? "from-[color:var(--mp-warning)]/30 to-transparent"
    : "from-[color:var(--mp-crimson)]/25 to-transparent";
  const Icon = props.icon;
  return (
    <div className={`relative overflow-hidden rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${tone} pointer-events-none`} />
      <div className="relative flex items-start justify-between">
        <div>
          <div className="text-xs text-[color:var(--mp-text-dim)] uppercase tracking-wider">{props.label}</div>
          <div className="mt-2 text-2xl font-semibold font-mono">{props.value}</div>
          {props.hint && <div className="mt-1 text-xs text-[color:var(--mp-text-dim)]">{props.hint}</div>}
        </div>
        <Icon className="size-5 text-[color:var(--mp-text-dim)]" />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();

  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list, refetchInterval: 10_000 });
  const tradesQ = useQuery({ queryKey: QK.activeTrades, queryFn: tradesApi.activeAll, refetchInterval: 10_000 });
  const botQ = useQuery({ queryKey: QK.botStatus, queryFn: botApi.status, refetchInterval: 10_000 });
  const notifQ = useQuery({
    queryKey: QK.notifications(false),
    queryFn: () => notificationsApi.list({ limit: 10 }),
    refetchInterval: 10_000,
  });

  const accounts = accountsQ.data ?? [];
  const trades = tradesQ.data ?? [];
  const bot = botQ.data;
  const notifs = notifQ.data ?? [];

  const dailyPnl = accounts.reduce((s, a) => s + a.daily_pnl, 0);
  const active = accounts.filter((a) => !a.paused && !a.breached).length;
  const paused = accounts.filter((a) => a.paused).length;
  const breached = accounts.filter((a) => a.breached).length;

  const handleForceCloseAll = async () => {
    const ok = await confirm({
      title: "Force close ALL positions?",
      description: "This will immediately close every open trade across every account.",
      destructive: true,
      confirmLabel: "Force close all",
    });
    if (!ok) return;
    try {
      const r = await botApi.forceCloseAll();
      toast.success(`Force-closed ${r.closed_count} position(s)`);
      qc.invalidateQueries({ queryKey: QK.activeTrades });
      qc.invalidateQueries({ queryKey: QK.accounts });
      qc.invalidateQueries({ queryKey: QK.botStatus });
    } catch {
      toast.error("Failed to force close positions");
    }
  };

  const bulkAccountAction = async (kind: "pause" | "resume") => {
    const ok = await confirm({
      title: kind === "pause" ? "Pause all accounts?" : "Resume all accounts?",
      description: kind === "pause"
        ? "All active accounts will stop accepting new signals."
        : "All paused accounts will resume accepting signals.",
    });
    if (!ok) return;
    const targets = accounts.filter((a) => kind === "pause" ? !a.paused : a.paused);
    await Promise.all(targets.map((a) =>
      kind === "pause" ? accountsApi.pause(a.account_key) : accountsApi.resume(a.account_key),
    ));
    toast.success(`${kind === "pause" ? "Paused" : "Resumed"} ${targets.length} account(s)`);
    qc.invalidateQueries({ queryKey: QK.accounts });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Command Dashboard</h1>
          <p className="text-sm text-[color:var(--mp-text-dim)]">Live overview of the Mirror Pupil bot and your prop accounts.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Accounts"
          value={accounts.length}
          hint={<>
            <span className="text-[color:var(--mp-success)]">{active} active</span>
            {" · "}
            <span className="text-[color:var(--mp-warning)]">{paused} paused</span>
            {" · "}
            <span className="text-[color:var(--mp-danger)]">{breached} breached</span>
          </>}
          icon={Users}
        />
        <StatCard
          label="Active trades"
          value={trades.length}
          hint={`${bot?.total_active_trades ?? trades.length} reported by bot`}
          icon={TrendingUp}
        />
        <StatCard
          label="P&L today"
          value={<span className={getPnLColor(dailyPnl)}>{formatCurrency(dailyPnl)}</span>}
          hint={`Across ${accounts.length} account(s)`}
          icon={DollarSign}
          tone={dailyPnl >= 0 ? "good" : "bad"}
        />
        <StatCard
          label="Bot status"
          value={
            <span className={bot?.status === "running"
              ? "text-[color:var(--mp-success)]"
              : "text-[color:var(--mp-text-dim)]"}>
              {bot?.status ?? "unknown"}
            </span>
          }
          hint={bot?.dry_run ? "dry-run mode" : "live trading"}
          icon={Bot}
          tone={bot?.status === "running" ? "good" : "warn"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="lg:col-span-2 rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)]">
          <header className="flex items-center justify-between p-4 border-b border-[color:var(--mp-border)]">
            <h2 className="font-semibold">Recent activity</h2>
            <Link to="/notifications" className="text-xs text-[color:var(--mp-text-dim)] hover:text-white">View all →</Link>
          </header>
          <ul className="divide-y divide-[color:var(--mp-border)]">
            {notifs.length === 0 && (
              <li className="p-6 text-center text-sm text-[color:var(--mp-text-dim)]">No notifications yet.</li>
            )}
            {notifs.map((n) => {
              const Icon = CAT_ICON[n.category];
              const sevColor = {
                CRITICAL: "border-[color:var(--mp-danger)]",
                ERROR: "border-[color:var(--mp-warning)]",
                WARNING: "border-[color:var(--mp-warning)]",
                INFO: "border-[color:var(--mp-info)]",
              }[n.severity];
              return (
                <li key={n.notification_id} className={`p-3 pl-4 border-l-4 ${sevColor} flex items-start gap-3`}>
                  <Icon className="size-4 mt-0.5 text-[color:var(--mp-text-dim)] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <div className="font-medium text-sm truncate">{n.title}</div>
                      <div className="text-[11px] text-[color:var(--mp-text-dim)] shrink-0">{formatTimeAgo(n.created_at)}</div>
                    </div>
                    <div className="text-xs text-[color:var(--mp-text-dim)] truncate">{n.message}</div>
                    {n.account_key && (
                      <div className="mt-1 text-[10px] font-mono text-[color:var(--mp-text-dim)]">{shortenKey(n.account_key)}</div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4 space-y-3">
          <h2 className="font-semibold mb-2">Quick actions</h2>
          <button
            type="button"
            onClick={handleForceCloseAll}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-md bg-[color:var(--mp-danger)] hover:bg-[color:var(--mp-danger)]/90 text-white font-medium text-sm"
          >
            <ShieldOff className="size-4" /> Force close all positions
          </button>
          <button
            type="button"
            onClick={() => bulkAccountAction("pause")}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-[color:var(--mp-border)] hover:bg-white/5 text-sm"
          >
            <PauseCircle className="size-4" /> Pause all accounts
          </button>
          <button
            type="button"
            onClick={() => bulkAccountAction("resume")}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-[color:var(--mp-border)] hover:bg-white/5 text-sm"
          >
            <PlayCircle className="size-4" /> Resume all accounts
          </button>
          <div className="border-t border-[color:var(--mp-border)] pt-3 grid grid-cols-2 gap-2 text-xs">
            <Link to="/trades" className="px-3 py-2 rounded-md bg-white/5 hover:bg-white/10 text-center">View trades</Link>
            <Link to="/history" className="px-3 py-2 rounded-md bg-white/5 hover:bg-white/10 text-center">View history</Link>
          </div>
        </section>
      </div>
    </div>
  );
}