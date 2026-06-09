import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Pause, Play, Pencil, Trash2, Plus, Search, AlertTriangle, ShieldCheck,
} from "lucide-react";
import { accountsApi, QK, riskProfilesApi } from "@/lib/mp/api";
import { formatBalance, formatCurrency, getPnLColor, shortenKey } from "@/lib/mp/utils";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { Account } from "@/lib/mp/types";

type FilterStatus = "all" | "active" | "paused" | "breached";

export function AccountsPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list, refetchInterval: 10_000 });
  const profilesQ = useQuery({ queryKey: QK.profiles, queryFn: riskProfilesApi.list });

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<FilterStatus>("all");
  const [editing, setEditing] = useState<Account | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  const filtered = useMemo(() => {
    const list = accountsQ.data ?? [];
    return list.filter((a) => {
      if (status === "active" && (a.paused || a.breached)) return false;
      if (status === "paused" && !a.paused) return false;
      if (status === "breached" && !a.breached) return false;
      if (!search) return true;
      const s = search.toLowerCase();
      return (
        a.account_key.toLowerCase().includes(s) ||
        (a.display_name?.toLowerCase().includes(s) ?? false) ||
        a.tl_email.toLowerCase().includes(s)
      );
    });
  }, [accountsQ.data, search, status]);

  const pauseM = useMutation({
    mutationFn: (k: string) => accountsApi.pause(k),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account paused"); },
    onError: () => toast.error("Failed to pause account"),
  });
  const resumeM = useMutation({
    mutationFn: (k: string) => accountsApi.resume(k),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account resumed"); },
    onError: () => toast.error("Failed to resume account"),
  });
  const deleteM = useMutation({
    mutationFn: (k: string) => accountsApi.delete(k),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account deleted"); },
    onError: () => toast.error("Failed to delete account"),
  });

  const onDelete = async (a: Account) => {
    const ok = await confirm({
      title: `Delete account?`,
      description: `Remove ${a.display_name ?? a.account_key} from Mirror Pupil. This cannot be undone.`,
      destructive: true, confirmLabel: "Delete",
    });
    if (ok) deleteM.mutate(a.account_key);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Accounts</h1>
          <p className="text-sm text-[color:var(--mp-text-dim)]">Manage your TradeLocker accounts and risk assignments.</p>
        </div>
        <Button onClick={() => setAddOpen(true)} className="gap-2 bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
          <Plus className="size-4" /> Add account
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-2.5 top-2.5 size-4 text-[color:var(--mp-text-dim)]" />
          <Input
            placeholder="Search by email or display name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={status} onValueChange={(v) => setStatus(v as FilterStatus)}>
          <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="breached">Breached</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {filtered.length === 0 && (
          <div className="col-span-full p-10 text-center text-sm text-[color:var(--mp-text-dim)] border border-dashed border-[color:var(--mp-border)] rounded-lg">
            No accounts match your filters.
          </div>
        )}
        {filtered.map((a) => {
          const profile = profilesQ.data?.find((p) => p.profile_id === a.risk_profile_id);
          return (
            <article key={a.account_key} className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold truncate">{a.display_name ?? a.tl_email}</h3>
                    {a.breached && (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-danger)]/15 text-[color:var(--mp-danger)] uppercase font-semibold">
                        <AlertTriangle className="size-3" /> Breached
                      </span>
                    )}
                    {a.paused && !a.breached && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-warning)]/15 text-[color:var(--mp-warning)] uppercase font-semibold">
                        Paused
                      </span>
                    )}
                    {!a.paused && !a.breached && (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-success)]/15 text-[color:var(--mp-success)] uppercase font-semibold">
                        <ShieldCheck className="size-3" /> Active
                      </span>
                    )}
                  </div>
                  <div className="font-mono text-[11px] text-[color:var(--mp-text-dim)] truncate mt-0.5">{a.account_key}</div>
                  <div className="text-xs text-[color:var(--mp-text-dim)] mt-0.5">{a.tl_server}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-mono text-lg font-semibold">{formatBalance(a.current_balance)}</div>
                  <div className={`text-xs font-mono ${getPnLColor(a.daily_pnl)}`}>{formatCurrency(a.daily_pnl)} today</div>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[color:var(--mp-text-dim)]">
                <div><div className="uppercase tracking-wider">Initial</div><div className="text-[color:var(--mp-text)] font-mono">{formatBalance(a.initial_balance)}</div></div>
                <div><div className="uppercase tracking-wider">Profile</div><div className="text-[color:var(--mp-text)] truncate">{profile?.profile_name ?? "—"}</div></div>
                <div><div className="uppercase tracking-wider">Lot ovr.</div><div className="text-[color:var(--mp-text)] font-mono">{a.lot_size_override ?? "—"}</div></div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {a.paused ? (
                  <Button size="sm" variant="outline" onClick={() => resumeM.mutate(a.account_key)} className="gap-1.5">
                    <Play className="size-3.5" /> Resume
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => pauseM.mutate(a.account_key)} className="gap-1.5">
                    <Pause className="size-3.5" /> Pause
                  </Button>
                )}
                <Button size="sm" variant="outline" onClick={() => setEditing(a)} className="gap-1.5">
                  <Pencil className="size-3.5" /> Edit
                </Button>
                <Button size="sm" variant="outline" onClick={() => onDelete(a)} className="gap-1.5 text-[color:var(--mp-danger)] hover:text-[color:var(--mp-danger)]">
                  <Trash2 className="size-3.5" /> Delete
                </Button>
              </div>
            </article>
          );
        })}
      </div>

      <AddAccountDialog open={addOpen} onOpenChange={setAddOpen} />
      <EditAccountDialog account={editing} onClose={() => setEditing(null)} />
    </div>
  );
}

function AddAccountDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const qc = useQueryClient();
  const [creds, setCreds] = useState({ email: "", password: "", server: "", prop_firm: "" });
  const [discovered, setDiscovered] = useState<Account[]>([]);
  const [manual, setManual] = useState({
    tl_email: "", tl_password: "", tl_prop_firm: "", tl_server: "", tl_account_id: "",
    display_name: "",
  });

  const discoverM = useMutation({
    mutationFn: () => accountsApi.discover(creds),
    onSuccess: (r) => { setDiscovered(r.accounts); toast.success(`Found ${r.accounts.length} account(s)`); },
    onError: () => toast.error("Discovery failed"),
  });

  const addOneM = useMutation({
    mutationFn: (a: Account) => accountsApi.create({
      tl_email: a.tl_email, tl_password: creds.password, tl_prop_firm: creds.prop_firm,
      tl_server: a.tl_server, tl_account_id: a.tl_account_id, display_name: a.display_name,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account added"); },
    onError: () => toast.error("Failed to add account"),
  });

  const manualAddM = useMutation({
    mutationFn: () => accountsApi.create(manual),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account added"); onOpenChange(false); },
    onError: () => toast.error("Failed to add account"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg border-[color:var(--mp-border)] bg-[color:var(--mp-base)]">
        <DialogHeader>
          <DialogTitle>Add account</DialogTitle>
          <DialogDescription>Discover from TradeLocker or enter details manually.</DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="discover">
          <TabsList className="grid grid-cols-2">
            <TabsTrigger value="discover">Discover</TabsTrigger>
            <TabsTrigger value="manual">Manual</TabsTrigger>
          </TabsList>
          <TabsContent value="discover" className="space-y-3 pt-3">
            <Field label="Email"><Input value={creds.email} onChange={(e) => setCreds({ ...creds, email: e.target.value })} /></Field>
            <Field label="Password"><Input type="password" value={creds.password} onChange={(e) => setCreds({ ...creds, password: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Server"><Input value={creds.server} onChange={(e) => setCreds({ ...creds, server: e.target.value })} /></Field>
              <Field label="Prop firm"><Input value={creds.prop_firm} onChange={(e) => setCreds({ ...creds, prop_firm: e.target.value })} /></Field>
            </div>
            <Button onClick={() => discoverM.mutate()} disabled={discoverM.isPending} className="w-full bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
              {discoverM.isPending ? "Discovering…" : "Discover accounts"}
            </Button>
            {discovered.length > 0 && (
              <ul className="border border-[color:var(--mp-border)] rounded-md divide-y divide-[color:var(--mp-border)] max-h-56 overflow-y-auto">
                {discovered.map((a) => (
                  <li key={a.account_key} className="flex items-center justify-between p-2">
                    <div>
                      <div className="text-sm">{a.display_name ?? a.tl_account_id}</div>
                      <div className="font-mono text-[11px] text-[color:var(--mp-text-dim)]">{a.tl_server}</div>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => addOneM.mutate(a)} disabled={addOneM.isPending}>Add</Button>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
          <TabsContent value="manual" className="space-y-3 pt-3">
            <Field label="Email"><Input value={manual.tl_email} onChange={(e) => setManual({ ...manual, tl_email: e.target.value })} /></Field>
            <Field label="Password"><Input type="password" value={manual.tl_password} onChange={(e) => setManual({ ...manual, tl_password: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Prop firm"><Input value={manual.tl_prop_firm} onChange={(e) => setManual({ ...manual, tl_prop_firm: e.target.value })} /></Field>
              <Field label="Server"><Input value={manual.tl_server} onChange={(e) => setManual({ ...manual, tl_server: e.target.value })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Account ID"><Input value={manual.tl_account_id} onChange={(e) => setManual({ ...manual, tl_account_id: e.target.value })} /></Field>
              <Field label="Display name"><Input value={manual.display_name} onChange={(e) => setManual({ ...manual, display_name: e.target.value })} /></Field>
            </div>
            <DialogFooter>
              <Button onClick={() => manualAddM.mutate()} disabled={manualAddM.isPending} className="bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
                {manualAddM.isPending ? "Adding…" : "Add account"}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

function EditAccountDialog({ account, onClose }: { account: Account | null; onClose: () => void }) {
  const qc = useQueryClient();
  const profilesQ = useQuery({ queryKey: QK.profiles, queryFn: riskProfilesApi.list });
  const [form, setForm] = useState<Partial<Account>>({});

  const open = !!account;
  const initial = account
    ? {
        display_name: account.display_name ?? "",
        lot_size_override: account.lot_size_override,
        risk_profile_id: account.risk_profile_id,
        max_concurrent_trades_override: account.max_concurrent_trades_override,
      }
    : {};

  const current = { ...initial, ...form };

  const saveM = useMutation({
    mutationFn: () => accountsApi.update(account!.account_key, current as Partial<Account>),
    onSuccess: () => { qc.invalidateQueries({ queryKey: QK.accounts }); toast.success("Account updated"); setForm({}); onClose(); },
    onError: () => toast.error("Failed to update account"),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { setForm({}); onClose(); } }}>
      <DialogContent className="max-w-lg border-[color:var(--mp-border)] bg-[color:var(--mp-base)]">
        <DialogHeader>
          <DialogTitle>Edit account</DialogTitle>
          <DialogDescription className="font-mono text-xs">{account?.account_key}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Field label="Display name">
            <Input
              value={current.display_name ?? ""}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Lot size override">
              <Input type="number" step="0.01"
                value={current.lot_size_override ?? ""}
                onChange={(e) => setForm({ ...form, lot_size_override: e.target.value === "" ? null : Number(e.target.value) })}
              />
            </Field>
            <Field label="Max concurrent trades">
              <Input type="number" step="1"
                value={current.max_concurrent_trades_override ?? ""}
                onChange={(e) => setForm({ ...form, max_concurrent_trades_override: e.target.value === "" ? null : Number(e.target.value) })}
              />
            </Field>
          </div>
          <Field label="Risk profile">
            <Select
              value={String(current.risk_profile_id ?? "none")}
              onValueChange={(v) => setForm({ ...form, risk_profile_id: v === "none" ? null : Number(v) })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">— None —</SelectItem>
                {profilesQ.data?.map((p) => (
                  <SelectItem key={p.profile_id} value={String(p.profile_id)}>{p.profile_name}{p.is_default ? " (default)" : ""}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setForm({}); onClose(); }}>Cancel</Button>
          <Button onClick={() => saveM.mutate()} disabled={saveM.isPending} className="bg-[color:var(--mp-red)] hover:bg-[color:var(--mp-red)]/90 text-white">
            {saveM.isPending ? "Saving…" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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