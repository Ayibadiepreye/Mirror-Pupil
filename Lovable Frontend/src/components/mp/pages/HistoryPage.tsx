import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Download } from "lucide-react";
import { accountsApi, channelsApi, QK, tradesApi } from "@/lib/mp/api";
import {
  formatBalance, formatCurrency, formatLagosTime, formatPrice, getPnLColor,
} from "@/lib/mp/utils";
import type { TradeHistory } from "@/lib/mp/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

type DateRange = "7" | "30" | "all";
type SortKey = keyof Pick<TradeHistory, "exit_time" | "symbol" | "pnl" | "lot_size" | "outcome">;

export function HistoryPage() {
  const [account, setAccount] = useState("all");
  const [range, setRange] = useState<DateRange>("all");
  const [symbol, setSymbol] = useState("");
  const [channel, setChannel] = useState("all");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "exit_time", dir: "desc" });
  const [exporting, setExporting] = useState(false);

  const accountsQ = useQuery({ queryKey: QK.accounts, queryFn: accountsApi.list });
  const channelsQ = useQuery({ queryKey: QK.channels, queryFn: channelsApi.list });
  const historyQ = useQuery({
    queryKey: QK.tradeHistory(account === "all" ? undefined : account),
    queryFn: () => tradesApi.historyAll({ account_key: account === "all" ? undefined : account }),
    refetchInterval: 10_000,
  });

  const filtered = useMemo(() => {
    let list = historyQ.data ?? [];
    const now = Date.now();
    if (range !== "all") {
      const days = range === "7" ? 7 : 30;
      const cutoff = now - days * 86_400_000;
      list = list.filter((t) => new Date(t.exit_time).getTime() >= cutoff);
    }
    if (channel !== "all") list = list.filter((t) => String(t.channel_id) === channel);
    if (symbol) list = list.filter((t) => t.symbol.toLowerCase().includes(symbol.toLowerCase()));
    list = [...list].sort((a, b) => {
      const av = a[sort.key]; const bv = b[sort.key];
      const cmp = av == null || bv == null ? 0 :
        typeof av === "number" && typeof bv === "number" ? av - bv :
        String(av).localeCompare(String(bv));
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [historyQ.data, range, channel, symbol, sort]);

  const stats = useMemo(() => {
    const total = filtered.length;
    const wins = filtered.filter((t) => t.outcome === "WIN");
    const losses = filtered.filter((t) => t.outcome === "LOSS");
    const sumPnl = filtered.reduce((s, t) => s + t.pnl, 0);
    const avgWin = wins.length ? wins.reduce((s, t) => s + t.pnl, 0) / wins.length : 0;
    const avgLoss = losses.length ? losses.reduce((s, t) => s + t.pnl, 0) / losses.length : 0;
    const largestWin = wins.reduce((m, t) => Math.max(m, t.pnl), 0);
    const largestLoss = losses.reduce((m, t) => Math.min(m, t.pnl), 0);
    const winRate = total ? Math.round((wins.length / total) * 100) : 0;
    return { total, wins: wins.length, losses: losses.length, winRate, sumPnl, avgWin, avgLoss, largestWin, largestLoss };
  }, [filtered]);

  const PAGE_SIZE = 50;
  const pageRows = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  const headers: { key: SortKey | null; label: string; align?: string }[] = [
    { key: "exit_time", label: "Exit (Lagos)" },
    { key: null, label: "Channel" },
    { key: "symbol", label: "Symbol" },
    { key: null, label: "Dir" },
    { key: null, label: "Entry", align: "text-right" },
    { key: null, label: "Exit", align: "text-right" },
    { key: "lot_size", label: "Lots", align: "text-right" },
    { key: "pnl", label: "P&L", align: "text-right" },
    { key: "outcome", label: "Outcome" },
    { key: null, label: "Reason" },
    { key: null, label: "Manual" },
  ];

  const onExport = async () => {
    try {
      setExporting(true);
      const blob = await tradesApi.exportCsvBlob(account === "all" ? undefined : account);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().slice(0, 10);
      a.download = `trade_history_${today}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("CSV exported");
    } catch {
      toast.error("Export failed");
    } finally {
      setExporting(false);
    }
  };

  const toggleSort = (k: SortKey | null) => {
    if (!k) return;
    setSort((s) => s.key === k ? { key: k, dir: s.dir === "asc" ? "desc" : "asc" } : { key: k, dir: "desc" });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Trade history</h1>
          <p className="text-sm text-[color:var(--mp-text-dim)]">Times shown in Lagos (WAT, UTC+1).</p>
        </div>
        <Button onClick={onExport} disabled={exporting} className="gap-2 bg-[color:var(--mp-crimson)] hover:bg-[color:var(--mp-crimson)]/90 text-white">
          <Download className="size-4" /> {exporting ? "Exporting…" : "Export CSV"}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select value={account} onValueChange={(v) => { setAccount(v); setPage(0); }}>
          <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All accounts</SelectItem>
            {accountsQ.data?.map((a) => (
              <SelectItem key={a.account_key} value={a.account_key}>{a.display_name ?? a.tl_email}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={range} onValueChange={(v) => { setRange(v as DateRange); setPage(0); }}>
          <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="all">All time</SelectItem>
          </SelectContent>
        </Select>
        <Input placeholder="Symbol…" value={symbol} onChange={(e) => { setSymbol(e.target.value); setPage(0); }} className="w-[160px]" />
        <Select value={channel} onValueChange={(v) => { setChannel(v); setPage(0); }}>
          <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All channels</SelectItem>
            {channelsQ.data?.map((c) => (
              <SelectItem key={c.channel_id} value={String(c.channel_id)}>{c.display_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        <StatTile label="Total" value={stats.total} />
        <StatTile label="Winners" value={`${stats.wins} (${stats.winRate}%)`} tone="good" />
        <StatTile label="Losers" value={stats.losses} tone="bad" />
        <StatTile label="Total P&L" value={formatCurrency(stats.sumPnl)} tone={stats.sumPnl >= 0 ? "good" : "bad"} />
        <StatTile label="Avg win" value={formatCurrency(stats.avgWin)} tone="good" />
        <StatTile label="Avg loss" value={formatCurrency(stats.avgLoss)} tone="bad" />
        <StatTile label="Largest win" value={formatCurrency(stats.largestWin)} tone="good" />
        <StatTile label="Largest loss" value={formatCurrency(stats.largestLoss)} tone="bad" />
      </div>

      <div className="rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-[color:var(--mp-app)] text-[color:var(--mp-text-dim)] uppercase text-[10px] tracking-wider">
              <tr>
                {headers.map((h) => (
                  <th key={h.label} className={`px-3 py-2 text-left ${h.align ?? ""}`}>
                    {h.key ? (
                      <button onClick={() => toggleSort(h.key)} className="inline-flex items-center gap-1 hover:text-white">
                        {h.label}
                        {sort.key === h.key && (sort.dir === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
                      </button>
                    ) : h.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.length === 0 ? (
                <tr><td colSpan={headers.length} className="text-center py-10 text-[color:var(--mp-text-dim)]">No trades match your filters.</td></tr>
              ) : pageRows.map((t) => (
                <tr key={t.history_id} className="border-t border-[color:var(--mp-border)] hover:bg-white/5">
                  <td className="px-3 py-2 font-mono whitespace-nowrap">{formatLagosTime(t.exit_time)}</td>
                  <td className="px-3 py-2">
                    <span className="inline-block text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-crimson)]/20">{t.channel_name ?? `#${t.channel_id}`}</span>
                  </td>
                  <td className="px-3 py-2 font-mono">{t.symbol}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${t.direction === "BUY" ? "bg-[color:var(--mp-success)]/15 text-[color:var(--mp-success)]" : "bg-[color:var(--mp-danger)]/15 text-[color:var(--mp-danger)]"}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-right">{formatPrice(t.entry_price, t.symbol)}</td>
                  <td className="px-3 py-2 font-mono text-right">{formatPrice(t.exit_price, t.symbol)}</td>
                  <td className="px-3 py-2 font-mono text-right">{t.lot_size.toFixed(2)}</td>
                  <td className={`px-3 py-2 font-mono text-right ${getPnLColor(t.pnl)}`}>{formatCurrency(t.pnl)}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                      t.outcome === "WIN" ? "bg-[color:var(--mp-success)]/15 text-[color:var(--mp-success)]"
                      : t.outcome === "LOSS" ? "bg-[color:var(--mp-danger)]/15 text-[color:var(--mp-danger)]"
                      : "bg-white/10 text-[color:var(--mp-text-dim)]"
                    }`}>{t.outcome}</span>
                  </td>
                  <td className="px-3 py-2 text-xs text-[color:var(--mp-text-dim)]">{t.close_reason}</td>
                  <td className="px-3 py-2">
                    {t.manual_action_type && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[color:var(--mp-warning)]/15 text-[color:var(--mp-warning)]">{t.manual_action_type}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-3 border-t border-[color:var(--mp-border)] text-xs text-[color:var(--mp-text-dim)]">
          <span>{filtered.length} trade(s)</span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Previous</Button>
            <span className="font-mono">{page + 1} / {totalPages}</span>
            <Button size="sm" variant="outline" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatTile({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "good" | "bad" }) {
  const color = tone === "good" ? "text-[color:var(--mp-success)]" : tone === "bad" ? "text-[color:var(--mp-danger)]" : "";
  return (
    <div className="rounded-md border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] p-3">
      <div className="text-[10px] uppercase tracking-wider text-[color:var(--mp-text-dim)]">{label}</div>
      <div className={`mt-1 font-mono text-base font-semibold ${color}`}>{value}</div>
    </div>
  );
}