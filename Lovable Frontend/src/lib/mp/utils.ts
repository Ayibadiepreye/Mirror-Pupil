// Mirror Pupil utility functions — see FRONTEND_REBUILD_PROMPT.md Utility section.

/** Relative time: "just now", "3m ago", "2h ago", "5d ago". */
export function formatTimeAgo(date: Date | string): string {
  const now = new Date();
  const then = typeof date === "string" ? new Date(date) : date;
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Convert UTC to Lagos time (WAT). Format: "Jun 08, 21:30". */
export function formatLagosTime(date: Date | string): string {
  const utc = typeof date === "string" ? new Date(date) : date;
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Africa/Lagos",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = formatter.formatToParts(utc);
  const month = parts.find(p => p.type === "month")?.value || "";
  const day = parts.find(p => p.type === "day")?.value || "";
  const hour = parts.find(p => p.type === "hour")?.value || "";
  const minute = parts.find(p => p.type === "minute")?.value || "";
  return `${month} ${day}, ${hour}:${minute}`;
}

export function formatCurrency(value: number, decimals = 2): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}$${Math.abs(value).toFixed(decimals)}`;
}

export function formatBalance(value: number): string {
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPrice(value: number, symbol: string): string {
  if (symbol.length === 6 && !symbol.startsWith("XAG") && !symbol.startsWith("XAU")) {
    return value.toFixed(5);
  }
  return value.toFixed(2);
}

export function getPnLColor(pnl: number): string {
  if (pnl > 0) return "text-[color:var(--mp-success)]";
  if (pnl < 0) return "text-[color:var(--mp-danger)]";
  return "text-[color:var(--mp-text-dim)]";
}

export function shortenKey(key: string): string {
  if (!key) return "";
  const [emailPart, accountPart] = key.split(":");
  if (accountPart && emailPart) {
    const e = emailPart.length > 12 ? `${emailPart.slice(0, 4)}…${emailPart.slice(-4)}` : emailPart;
    return `${e}:${accountPart}`;
  }
  return key.length > 16 ? `${key.slice(0, 8)}…${key.slice(-5)}` : key;
}