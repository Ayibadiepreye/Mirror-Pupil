import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Star, Trash2, ShieldOff, PauseCircle, PlayCircle } from "lucide-react";
import { accountsApi, botApi, channelsApi, QK, riskProfilesApi } from "@/lib/mp/api";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import type { Channel, RiskProfile } from "@/lib/mp/types";
import { useMirrorPupilWebSocket } from "@/lib/mp/ws";

export function SettingsPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-[color:var(--mp-text-dim)]">Channels, risk profiles, and bot configuration.</p>
      </div>
      <Tabs defaultValue="channels">
        <TabsList className="grid grid-cols-3 max-w-md">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="profiles">Risk Profiles</TabsTrigger>
          <TabsTrigger value="bot">Bot Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="channels" className="pt-4"><ChannelsTab /></TabsContent>
        <TabsContent value="profiles" className="pt-4"><ProfilesTab /></TabsContent>
        <TabsContent value="bot" className="pt-4"><BotSettingsTab /></TabsContent>
      </Tabs>
    </div>
  );
}

/* ─────────────── Channels ─────────────── */
function emptyChannel(): Channel {
  return {
    channel_id: 0, display_name: "", signal_prefix: "",
    entry_logic_module: "billirichy.entry",
    management_logic_module: "billirichy.management",
    priority: 10, enabled: true, notes: null,
  };
}

function ChannelsTab() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const channelsQ = useQuery({ queryKey: QK.channels, queryFn: channelsApi.list });
  const [editing, setEditing] = useState<Channel | null>(null);
  const [adding, setAdding] = useState(false);

  const toggleM = useMutation({
    mutationFn: ({ id, enable }: { id: number; enable: boolean }) =>
      enable ? channelsApi.enable(id) : channelsApi.disable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.channels }),
  });
  const deleteM = useMutation({
    mutationFn: (id: number) => channelsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.channels }); toast.success("Channel deleted"); },
  });

  const onDelete = async (c: Channel) => {
    const ok = await confirm({ title: `Delete channel "${c.display_name}"?`, destructive: true, confirmLabel: "Delete" });
    if (ok) deleteM.mutate(c.channel_id);
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button onClick={() => setAdding(true)} className="gap-2 bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
          <Plus className="size-4" /> Add channel
        </Button>
      </div>
      <div className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-[color:var(--mp-app)] text-[10px] uppercase tracking-wider text-[color:var(--mp-text-dim)]">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Channel ID</th>
              <th className="px-3 py-2 text-left">Prefix</th>
              <th className="px-3 py-2 text-left">Priority</th>
              <th className="px-3 py-2 text-left">Enabled</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(channelsQ.data ?? []).map((c) => (
              <tr key={c.channel_id} className="border-t border-[color:var(--mp-border)] hover:bg-white/5">
                <td className="px-3 py-2 font-medium">{c.display_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{c.channel_id}</td>
                <td className="px-3 py-2 font-mono text-xs">{c.signal_prefix}</td>
                <td className="px-3 py-2 font-mono">{c.priority}</td>
                <td className="px-3 py-2">
                  <Switch checked={c.enabled} onCheckedChange={(v) => toggleM.mutate({ id: c.channel_id, enable: v })} />
                </td>
                <td className="px-3 py-2 text-right">
                  <Button size="sm" variant="ghost" onClick={() => setEditing(c)}><Pencil className="size-3.5" /></Button>
                  <Button size="sm" variant="ghost" className="text-[color:var(--mp-danger)]" onClick={() => onDelete(c)}><Trash2 className="size-3.5" /></Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ChannelDialog
        open={adding || !!editing}
        initial={editing ?? emptyChannel()}
        isEdit={!!editing}
        onClose={() => { setAdding(false); setEditing(null); }}
      />
    </div>
  );
}

function ChannelDialog({ open, initial, isEdit, onClose }: { open: boolean; initial: Channel; isEdit: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Channel>(initial);
  // Reset when initial changes
  if (open && form.channel_id !== initial.channel_id && !isEdit) {
    // noop — handled via key in parent if needed
  }

  const saveM = useMutation({
    mutationFn: () =>
      isEdit ? channelsApi.update(initial.channel_id, form) : channelsApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.channels }); toast.success(isEdit ? "Channel updated" : "Channel created"); onClose(); },
    onError: () => toast.error("Save failed"),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="border-[color:var(--mp-border)] bg-[color:var(--mp-base)] max-w-lg">
        <DialogHeader><DialogTitle>{isEdit ? "Edit channel" : "Add channel"}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Channel ID (Telegram)"><Input type="number" value={form.channel_id || ""} onChange={(e) => setForm({ ...form, channel_id: Number(e.target.value) })} disabled={isEdit} /></Field>
            <Field label="Display name"><Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Signal prefix"><Input value={form.signal_prefix} onChange={(e) => setForm({ ...form, signal_prefix: e.target.value })} /></Field>
            <Field label="Priority"><Input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Entry logic module">
              <select
                value={form.entry_logic_module}
                onChange={(e) => setForm({ ...form, entry_logic_module: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="billirichy.entry">billirichy.entry</option>
                <option value="firepips.entry">firepips.entry</option>
              </select>
            </Field>
            <Field label="Management logic module">
              <select
                value={form.management_logic_module}
                onChange={(e) => setForm({ ...form, management_logic_module: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="billirichy.management">billirichy.management</option>
                <option value="firepips.management">firepips.management</option>
              </select>
            </Field>
          </div>
          <Field label="Notes"><Textarea value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value || null })} /></Field>
          <div className="flex items-center gap-2">
            <Switch checked={form.enabled} onCheckedChange={(v) => setForm({ ...form, enabled: v })} />
            <Label className="text-sm">Enabled</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => saveM.mutate()} disabled={saveM.isPending} className="bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
            {saveM.isPending ? "Saving…" : isEdit ? "Save" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ─────────────── Risk Profiles ─────────────── */
function emptyProfile(): Omit<RiskProfile, "profile_id"> {
  return {
    profile_name: "", is_default: false,
    max_risk_per_trade_pct: 0.5, daily_loss_pct: 4, daily_trailing: true,
    overall_loss_pct: 8, overall_trailing: true, overall_trail_from_closed_balance: true,
    profit_lock_pct: null, profit_lock_floor_pct: null,
    payout_buffer_pct: 1, max_concurrent_trades: 5, commission_per_lot: 7,
    safety_buffer_pct: 0.5, notes: null,
  };
}

function ProfilesTab() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const profilesQ = useQuery({ queryKey: QK.profiles, queryFn: riskProfilesApi.list });
  const [editing, setEditing] = useState<RiskProfile | null>(null);
  const [adding, setAdding] = useState(false);

  const setDefaultM = useMutation({
    mutationFn: (p: RiskProfile) => riskProfilesApi.patch(p.profile_id, { is_default: true }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.profiles }); toast.success("Default profile updated"); },
  });
  const deleteM = useMutation({
    mutationFn: (id: number) => riskProfilesApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.profiles }); toast.success("Profile deleted"); },
  });
  const onDelete = async (p: RiskProfile) => {
    const ok = await confirm({ title: `Delete profile "${p.profile_name}"?`, destructive: true, confirmLabel: "Delete" });
    if (ok) deleteM.mutate(p.profile_id);
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button onClick={() => setAdding(true)} className="gap-2 bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
          <Plus className="size-4" /> Add profile
        </Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(profilesQ.data ?? []).map((p) => (
          <article key={p.profile_id} className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold flex items-center gap-2">
                  {p.profile_name}
                  {p.is_default && (
                    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-warning)]/20 text-[color:var(--mp-warning)] uppercase">
                      <Star className="size-3" /> Default
                    </span>
                  )}
                </h3>
                {p.notes && <p className="text-xs text-[color:var(--mp-text-dim)] mt-1">{p.notes}</p>}
              </div>
              <div className="flex gap-1">
                {!p.is_default && (
                  <Button size="sm" variant="ghost" title="Set default" onClick={() => setDefaultM.mutate(p)}><Star className="size-3.5" /></Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => setEditing(p)}><Pencil className="size-3.5" /></Button>
                <Button size="sm" variant="ghost" className="text-[color:var(--mp-danger)]" onClick={() => onDelete(p)}><Trash2 className="size-3.5" /></Button>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <PStat label="Per trade" value={`${p.max_risk_per_trade_pct}%`} />
              <PStat label="Daily" value={`${p.daily_loss_pct}%${p.daily_trailing ? " trail" : ""}`} />
              <PStat label="Overall" value={`${p.overall_loss_pct}%${p.overall_trailing ? " trail" : ""}`} />
              <PStat label="Max trades" value={p.max_concurrent_trades} />
              <PStat label="Commission" value={`$${p.commission_per_lot}/lot`} />
              <PStat label="Safety" value={`${p.safety_buffer_pct}%`} />
            </div>
          </article>
        ))}
      </div>
      <ProfileDialog
        open={adding || !!editing}
        initial={editing ?? null}
        onClose={() => { setAdding(false); setEditing(null); }}
      />
    </div>
  );
}

function PStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded bg-white/5 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-[color:var(--mp-text-dim)]">{label}</div>
      <div className="font-mono">{value}</div>
    </div>
  );
}

function ProfileDialog({ open, initial, onClose }: { open: boolean; initial: RiskProfile | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Omit<RiskProfile, "profile_id">>(initial ?? emptyProfile());
  // Re-initialize when initial changes
  useState(() => { setForm(initial ?? emptyProfile()); });

  const saveM = useMutation({
    mutationFn: () =>
      initial
        ? riskProfilesApi.update(initial.profile_id, { ...form, profile_id: initial.profile_id })
        : riskProfilesApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.profiles }); toast.success("Saved"); onClose(); },
    onError: () => toast.error("Save failed"),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="border-[color:var(--mp-border)] bg-[color:var(--mp-base)] max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{initial ? "Edit profile" : "Add profile"}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Profile name"><Input value={form.profile_name} onChange={(e) => setForm({ ...form, profile_name: e.target.value })} /></Field>
            <div className="flex items-end gap-2">
              <Switch checked={form.is_default} onCheckedChange={(v) => setForm({ ...form, is_default: v })} />
              <Label className="text-sm">Default profile</Label>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Max risk / trade %"><Input type="number" step="0.01" value={form.max_risk_per_trade_pct} onChange={(e) => setForm({ ...form, max_risk_per_trade_pct: Number(e.target.value) })} /></Field>
            <Field label="Daily loss %"><Input type="number" step="0.1" value={form.daily_loss_pct} onChange={(e) => setForm({ ...form, daily_loss_pct: Number(e.target.value) })} /></Field>
            <div className="flex items-end gap-2 pb-2">
              <Switch checked={form.daily_trailing} onCheckedChange={(v) => setForm({ ...form, daily_trailing: v })} />
              <Label className="text-sm">Daily trail</Label>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Overall loss %"><Input type="number" step="0.1" value={form.overall_loss_pct} onChange={(e) => setForm({ ...form, overall_loss_pct: Number(e.target.value) })} /></Field>
            <div className="flex items-end gap-2 pb-2">
              <Switch checked={form.overall_trailing} onCheckedChange={(v) => setForm({ ...form, overall_trailing: v })} />
              <Label className="text-sm">Overall trail</Label>
            </div>
            <div className="flex items-end gap-2 pb-2">
              <Switch checked={form.overall_trail_from_closed_balance} onCheckedChange={(v) => setForm({ ...form, overall_trail_from_closed_balance: v })} />
              <Label className="text-sm">From closed bal.</Label>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Profit lock % (optional)">
              <Input type="number" step="0.1" value={form.profit_lock_pct ?? ""} onChange={(e) => setForm({ ...form, profit_lock_pct: e.target.value === "" ? null : Number(e.target.value) })} />
            </Field>
            <Field label="Profit lock floor % (optional)">
              <Input type="number" step="0.1" value={form.profit_lock_floor_pct ?? ""} onChange={(e) => setForm({ ...form, profit_lock_floor_pct: e.target.value === "" ? null : Number(e.target.value) })} />
            </Field>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <Field label="Payout buffer %"><Input type="number" step="0.1" value={form.payout_buffer_pct} onChange={(e) => setForm({ ...form, payout_buffer_pct: Number(e.target.value) })} /></Field>
            <Field label="Max concurrent"><Input type="number" value={form.max_concurrent_trades} onChange={(e) => setForm({ ...form, max_concurrent_trades: Number(e.target.value) })} /></Field>
            <Field label="Commission/lot"><Input type="number" step="0.1" value={form.commission_per_lot} onChange={(e) => setForm({ ...form, commission_per_lot: Number(e.target.value) })} /></Field>
            <Field label="Safety buffer %"><Input type="number" step="0.01" value={form.safety_buffer_pct} onChange={(e) => setForm({ ...form, safety_buffer_pct: Number(e.target.value) })} /></Field>
          </div>
          <Field label="Notes"><Textarea value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value || null })} /></Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => saveM.mutate()} disabled={saveM.isPending} className="bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
            {saveM.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ─────────────── Bot Settings ─────────────── */
function BotSettingsTab() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const ws = useMirrorPupilWebSocket();
  const botQ = useQuery({ queryKey: QK.botStatus, queryFn: botApi.status, refetchInterval: 10_000 });
  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list });

  const forceCloseAll = async () => {
    const ok = await confirm({
      title: "Force close ALL positions?",
      description: "This will close every open trade across every account.",
      destructive: true, confirmLabel: "Force close all",
    });
    if (!ok) return;
    const r = await botApi.forceCloseAll();
    toast.success(`Closed ${r.closed_count} position(s)`);
    qc.invalidateQueries({ queryKey: QK.activeTrades });
    qc.invalidateQueries({ queryKey: QK.botStatus });
  };
  const bulk = async (kind: "pause" | "resume") => {
    const targets = (accountsQ.data ?? []).filter((a) => kind === "pause" ? !a.paused : a.paused);
    await Promise.all(targets.map((a) => kind === "pause" ? accountsApi.pause(a.account_key) : accountsApi.resume(a.account_key)));
    toast.success(`${kind === "pause" ? "Paused" : "Resumed"} ${targets.length}`);
    qc.invalidateQueries({ queryKey: QK.accounts });
  };

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4 space-y-3">
        <h3 className="font-semibold">Trading hours</h3>
        <div className="flex items-center justify-between">
          <Label>Allow weekend trading</Label>
          <Switch checked={!!botQ.data?.allow_weekend_trading} disabled />
        </div>
        <div className="flex items-center justify-between">
          <Label>Allow end-of-day trading</Label>
          <Switch checked={!!botQ.data?.allow_eod_trading} disabled />
        </div>
        <p className="text-[11px] text-[color:var(--mp-text-dim)]">Trading-hours toggles are read-only here; configure them via the Bot Control page.</p>
      </section>

      <section className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4 space-y-3">
        <h3 className="font-semibold">Emergency actions</h3>
        <div className="flex flex-wrap gap-2">
          <Button onClick={forceCloseAll} className="gap-2 bg-[color:var(--mp-danger)] hover:bg-[color:var(--mp-danger)]/90 text-white">
            <ShieldOff className="size-4" /> Force close all
          </Button>
          <Button variant="outline" onClick={() => bulk("pause")} className="gap-2"><PauseCircle className="size-4" /> Pause all</Button>
          <Button variant="outline" onClick={() => bulk("resume")} className="gap-2"><PlayCircle className="size-4" /> Resume all</Button>
        </div>
      </section>

      <section className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4">
        <h3 className="font-semibold mb-3">System info</h3>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-[color:var(--mp-text-dim)]">Bot status</dt>
          <dd className="font-mono">{botQ.data?.status ?? "—"}</dd>
          <dt className="text-[color:var(--mp-text-dim)]">Dry run</dt>
          <dd className="font-mono">{botQ.data?.dry_run ? "yes" : "no"}</dd>
          <dt className="text-[color:var(--mp-text-dim)]">Realtime stream</dt>
          <dd className="font-mono">{ws}</dd>
          <dt className="text-[color:var(--mp-text-dim)]">Active trades</dt>
          <dd className="font-mono">{botQ.data?.total_active_trades ?? 0}</dd>
          <dt className="text-[color:var(--mp-text-dim)]">App version</dt>
          <dd className="font-mono">Mirror Pupil v5.1</dd>
        </dl>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs uppercase tracking-wider text-[color:var(--mp-text-dim)]">{label}</Label>
      {children}
    </div>
  );
}