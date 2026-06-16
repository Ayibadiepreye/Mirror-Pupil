import { useQuery, useQueryClient, useMutation } from "@tantml:function_calls>
<invoke name="str_replace">
<parameter name="newStr">import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  Bot, PauseCircle, PlayCircle, RotateCw, ShieldOff,
} from "lucide-react";
import { useState } from "react";
import { accountsApi, botApi, QK } from "@/lib/mp/api";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { shortenKey } from "@/lib/mp/utils";
import { useAuth } from "@/lib/mp/auth-context";

export function BotControlPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const { isSuperAdmin } = useAuth();
  const botQ = useQuery({ queryKey: QK.botStatus, queryFn: botApi.status, refetchInterval: 10_000 });
  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list });
  const [forceAccount, setForceAccount] = useState("");

  const controlM = useMutation({
    mutationFn: (action: "start" | "stop") => botApi.control(action),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: QK.botStatus }); toast.success(`Bot ${r.status}`); },
    onError: () => toast.error("Bot control failed"),
  });

  const bot = botQ.data;
  const running = bot?.status === "running";

  const start = async () => {
    if (!isSuperAdmin) { toast.error("Admin access required"); return; }
    if (!(await confirm({ title: "Start bot?", description: "Resume processing signals and executing trades." }))) return;
    controlM.mutate("start");
  };
  const stop = async () => {
    if (!isSuperAdmin) { toast.error("Admin access required"); return; }
    if (!(await confirm({ title: "Stop bot?", description: "Bot will stop accepting signals. Open positions remain.", destructive: true }))) return;
    controlM.mutate("stop");
  };
  const restart = async () => {
    if (!isSuperAdmin) { toast.error("Admin access required"); return; }
    if (!(await confirm({ title: "Restart bot?", description: "Bot will stop then start." }))) return;
    await botApi.control("stop");
    await new Promise((r) => setTimeout(r, 250));
    await botApi.control("start");
    qc.invalidateQueries({ queryKey: QK.botStatus });
    toast.success("Bot restarted");
  };
  const closeAll = async () => {
    if (!isSuperAdmin) { toast.error("Admin access required"); return; }
    if (!(await confirm({ title: "Force close ALL positions?", destructive: true, confirmLabel: "Force close all" }))) return;
    const r = await botApi.forceCloseAll();
    toast.success(`Closed ${r.closed_count} position(s)`);
    qc.invalidateQueries({ queryKey: QK.activeTrades });
  };
  const closeAccount = async () => {
    if (!isSuperAdmin) { toast.error("Admin access required"); return; }
    if (!forceAccount) { toast.error("Pick an account"); return; }
    if (!(await confirm({ title: `Force close all positions for ${shortenKey(forceAccount)}?`, destructive: true }))) return;
    const r = await botApi.forceCloseAccount(forceAccount);
    toast.success(`Closed ${r.closed_count} position(s)`);
    qc.invalidateQueries({ queryKey: QK.activeTrades });
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bot control</h1>
        <p className="text-sm text-[color:var(--mp-text-dim)]">Operate the Mirror Pupil bot and run emergency actions.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Status */}
        <section className="lg:col-span-2 rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className={`size-12 rounded-lg grid place-items-center ${running ? "bg-[color:var(--mp-success)]/15 text-[color:var(--mp-success)]" : "bg-white/5 text-[color:var(--mp-text-dim)]"}`}>
                <Bot className="size-6" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[color:var(--mp-text-dim)]">Bot status</div>
                <div className="text-2xl font-semibold capitalize">{bot?.status ?? "…"}</div>
                {bot?.dry_run && <div className="text-[10px] uppercase text-[color:var(--mp-warning)] tracking-widest mt-0.5">Dry-run mode</div>}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 justify-end">
              {!running ? (
                <Button onClick={start} disabled={!isSuperAdmin} className="gap-2 bg-[color:var(--mp-success)] hover:bg-[color:var(--mp-success)]/90 text-black disabled:opacity-50 disabled:cursor-not-allowed">
                  <PlayCircle className="size-4" /> Start
                </Button>
              ) : (
                <Button onClick={stop} disabled={!isSuperAdmin} variant="outline" className="gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
                  <PauseCircle className="size-4" /> Stop
                </Button>
              )}
              <Button onClick={restart} disabled={!isSuperAdmin} variant="outline" className="gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
                <RotateCw className="size-4" /> Restart
              </Button>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Tile label="Active accts" value={bot?.active_accounts ?? 0} />
            <Tile label="Paused accts" value={bot?.paused_accounts ?? 0} />
            <Tile label="Breached accts" value={bot?.breached_accounts ?? 0} tone="bad" />
            <Tile label="Open trades" value={bot?.total_active_trades ?? 0} />
          </div>
        </section>

        {/* Toggles */}
        <section className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-5 space-y-3">
          <h2 className="font-semibold">Trading hours</h2>
          <div className="flex items-center justify-between">
            <Label>Allow weekend trading</Label>
            <Switch checked={!!bot?.allow_weekend_trading} disabled />
          </div>
          <div className="flex items-center justify-between">
            <Label>Allow end-of-day trading</Label>
            <Switch checked={!!bot?.allow_eod_trading} disabled />
          </div>
          <p className="text-[11px] text-[color:var(--mp-text-dim)]">
            Toggles reflect backend config; flip them in the bot config file or via your admin API.
          </p>
        </section>
      </div>

      {/* Emergency */}
      <section className="rounded-lg border border-[color:var(--mp-danger)]/40 bg-gradient-to-br from-[color:var(--mp-crimson)]/10 to-transparent p-5 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldOff className="size-5 text-[color:var(--mp-danger)]" />
          <h2 className="font-semibold">Emergency actions</h2>
          {!isSuperAdmin && <span className="text-xs text-[color:var(--mp-text-dim)]">(Admin only)</span>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={closeAll} disabled={!isSuperAdmin} className="gap-2 bg-[color:var(--mp-danger)] hover:bg-[color:var(--mp-danger)]/90 text-white disabled:opacity-50 disabled:cursor-not-allowed">
            <ShieldOff className="size-4" /> Force close all
          </Button>
          <div className="flex items-center gap-2">
            <Select value={forceAccount} onValueChange={setForceAccount} disabled={!isSuperAdmin}>
              <SelectTrigger className="w-[260px] disabled:opacity-50 disabled:cursor-not-allowed"><SelectValue placeholder="Pick account…" /></SelectTrigger>
              <SelectContent>
                {(accountsQ.data ?? []).map((a) => (
                  <SelectItem key={a.account_key} value={a.account_key}>{a.display_name ?? a.tl_email}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={closeAccount} disabled={!isSuperAdmin} variant="outline" className="gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <ShieldOff className="size-4" /> Close account
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

function Tile({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "bad" }) {
  return (
    <div className="rounded-md border border-[color:var(--mp-border)] bg-[color:var(--mp-app)] p-3">
      <div className="text-[10px] uppercase tracking-wider text-[color:var(--mp-text-dim)]">{label}</div>
      <div className={`mt-1 font-mono text-xl font-semibold ${tone === "bad" ? "text-[color:var(--mp-danger)]" : ""}`}>{value}</div>
    </div>
  );
}