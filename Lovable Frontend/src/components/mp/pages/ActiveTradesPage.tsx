import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, CheckCircle2, Scale, Scissors, X } from "lucide-react";
import { accountsApi, channelsApi, QK, tradesApi } from "@/lib/mp/api";
import {
  formatCurrency, formatPrice, formatTimeAgo, shortenKey,
} from "@/lib/mp/utils";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useMirrorPupilWebSocket } from "@/lib/mp/ws";
import type { ActiveTrade } from "@/lib/mp/types";

type SortKey = "time" | "symbol" | "lots";

export function ActiveTradesPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const ws = useMirrorPupilWebSocket();

  const tradesQ = useQuery({
    queryKey: QK.activeTrades,
    queryFn: tradesApi.activeAll,
    refetchInterval: ws === "connected" ? 30_000 : 5_000,
  });
  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list });
  const channelsQ = useQuery({ queryKey: QK.channels, queryFn: channelsApi.list });

  const [accountKey, setAccountKey] = useState("all");
  const [symbol, setSymbol] = useState("");
  const [channelId, setChannelId] = useState("all");
  const [sort, setSort] = useState<SortKey>("time");

  const filtered = useMemo(() => {
    let list = tradesQ.data ?? [];
    if (accountKey !== "all") list = list.filter((t) => t.account_key === accountKey);
    if (channelId !== "all") list = list.filter((t) => String(t.channel_id) === channelId);
    if (symbol) list = list.filter((t) => t.symbol.toLowerCase().includes(symbol.toLowerCase()));
    list = [...list].sort((a, b) => {
      if (sort === "symbol") return a.symbol.localeCompare(b.symbol);
      if (sort === "lots") return b.lot_size - a.lot_size;
      return new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime();
    });
    return list;
  }, [tradesQ.data, accountKey, channelId, symbol, sort]);

  const closeM = useMutation({
    mutationFn: (id: number) => tradesApi.close(id),
    onSuccess: (r) => { toast.success(r.message); qc.invalidateQueries({ queryKey: QK.activeTrades }); },
    onError: () => toast.error("Failed to close trade"),
  });
  const beM = useMutation({
    mutationFn: (id: number) => tradesApi.breakeven(id),
    onSuccess: (r) => { toast.success(r.message); qc.invalidateQueries({ queryKey: QK.activeTrades }); },
    onError: () => toast.error("Failed to set breakeven"),
  });
  const partialM = useMutation({
    mutationFn: ({ id, pct }: { id: number; pct: 25 | 50 | 75 }) => tradesApi.partial(id, pct),
    onSuccess: (r) => {
      toast.success(`${r.message} — remaining ${r.remaining_lots} lots`);
      qc.invalidateQueries({ queryKey: QK.activeTrades });
    },
    onError: () => toast.error("Failed to take partial"),
  });

  const doClose = async (t: ActiveTrade) => {
    const ok = await confirm({
      title: `Close entire position for ${t.symbol}?`,
      description: `${t.direction} ${t.lot_size} lots from ${shortenKey(t.account_key)}.`,
      destructive: true, confirmLabel: "Close position",
    });
    if (ok) closeM.mutate(t.trade_id);
  };
  const doBe = async (t: ActiveTrade) => {
    const ok = await confirm({
      title: `Set stop loss to breakeven for ${t.symbol}?`,
      description: `SL will be moved to entry price ${formatPrice(t.entry_price, t.symbol)}.`,
    });
    if (ok) beM.mutate(t.trade_id);
  };
  const doPartial = async (t: ActiveTrade, pct: 25 | 50 | 75) => {
    const ok = await confirm({
      title: `Close ${pct}% of ${t.symbol} position?`,
      description: `${t.lot_size} lots open. ${pct}% will be closed at market.`,
    });
    if (ok) partialM.mutate({ id: t.trade_id, pct });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Active trades</h1>
          <p className="text-sm text-[color:var(--mp-text-dim)]">Manage open positions in real time. {ws === "connected" ? "Realtime stream active." : "Polling every 5s."}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <Select value={accountKey} onValueChange={setAccountKey}>
          <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All accounts</SelectItem>
            {accountsQ.data?.map((a) => (
              <SelectItem key={a.account_key} value={a.account_key}>{a.display_name ?? a.tl_email}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={channelId} onValueChange={setChannelId}>
          <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All channels</SelectItem>
            {channelsQ.data?.map((c) => (
              <SelectItem key={c.channel_id} value={String(c.channel_id)}>{c.display_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Symbol filter…"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-[180px]"
        />
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="time">Newest first</SelectItem>
            <SelectItem value="symbol">By symbol</SelectItem>
            <SelectItem value="lots">By lot size</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-[color:var(--mp-border)] rounded-lg">
          <p className="text-[color:var(--mp-text-dim)] text-sm">No active trades.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((t) => {
            const isBuy = t.direction === "BUY";
            const dirColor = isBuy ? "text-[color:var(--mp-success)]" : "text-[color:var(--mp-danger)]";
            const dirBg = isBuy ? "bg-[color:var(--mp-success)]/10" : "bg-[color:var(--mp-danger)]/10";
            const Icon = isBuy ? ArrowUpRight : ArrowDownRight;
            return (
              <article key={t.trade_id} className="relative rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] overflow-hidden">
                <div className={`absolute inset-0 ${dirBg} opacity-30 pointer-events-none`} />
                <div className="relative p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 font-semibold ${dirColor} ${dirBg} px-2 py-1 rounded text-xs`}>
                        <Icon className="size-3.5" /> {t.direction}
                      </span>
                      <h3 className="font-mono font-semibold text-lg">{t.symbol}</h3>
                      {t.status === "pending" && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-500">
                          PENDING
                        </span>
                      )}
                      {t.tp1_hit && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[color:var(--mp-success)]/20 text-[color:var(--mp-success)]">
                          <CheckCircle2 className="size-3" /> TP1
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-[color:var(--mp-text-dim)]">{formatTimeAgo(t.entry_time)}</span>
                  </div>

                  {t.channel_name && (
                    <div className="inline-flex items-center text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-crimson)]/20 text-[color:var(--mp-text)] uppercase tracking-wider">
                      {t.channel_name}
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <Stat label="Entry" value={formatPrice(t.entry_price, t.symbol)} />
                    <Stat label="SL" value={t.sl != null ? formatPrice(t.sl, t.symbol) : "—"} />
                    <Stat label="TP" value={t.tp != null ? formatPrice(t.tp, t.symbol) : "—"} />
                    <Stat label="Lots" value={t.lot_size.toFixed(2)} />
                    <Stat label="Risk" value={t.risk_usd != null ? formatCurrency(-t.risk_usd) : "—"} />
                    <Stat 
                      label="P&L" 
                      value={t.current_pnl != null ? formatCurrency(t.current_pnl) : "—"} 
                      className={t.current_pnl != null && t.current_pnl !== 0 ? (t.current_pnl > 0 ? "text-[color:var(--mp-success)]" : "text-[color:var(--mp-danger)]") : undefined}
                    />
                  </div>

                  <div className="text-[10px] font-mono text-[color:var(--mp-text-dim)] truncate">{shortenKey(t.account_key)}</div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button size="sm" variant="outline" className="gap-1.5 text-[color:var(--mp-danger)] hover:text-[color:var(--mp-danger)]" onClick={() => doClose(t)}>
                      <X className="size-3.5" /> Close
                    </Button>
                    <Button size="sm" variant="outline" className="gap-1.5" onClick={() => doBe(t)} disabled={t.status !== "filled"}>
                      <Scale className="size-3.5" /> Breakeven
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button size="sm" variant="outline" className="gap-1.5" disabled={t.status !== "filled"}>
                          <Scissors className="size-3.5" /> Partial
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => doPartial(t, 25)}>Close 25%</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => doPartial(t, 50)}>Close 50%</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => doPartial(t, 75)}>Close 75%</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, className }: { label: string; value: React.ReactNode; className?: string }) {
  return (
    <div className="rounded-md bg-white/5 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-[color:var(--mp-text-dim)]">{label}</div>
      <div className={`font-mono truncate ${className || "text-[color:var(--mp-text)]"}`}>{value}</div>
    </div>
  );
}