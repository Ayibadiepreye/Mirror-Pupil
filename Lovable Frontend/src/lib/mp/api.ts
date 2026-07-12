/**
 * Mirror Pupil API client.
 * - Real HTTP via axios → backend at VITE_API_URL.
 * - When VITE_USE_MOCK === "true" (dev only), returns in-memory mock data.
 *   Production builds (VITE_USE_MOCK unset/false) always hit the real API.
 */
import axios, { type AxiosInstance } from "axios";
import type {
  Account, ActiveTrade, BotStatus, Channel, Notification,
  RiskProfile, TradeHistory, User,
} from "./types";
import * as mock from "./mock-data";
import { getSession, refreshToken } from "./auth";

export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
export const WS_BASE_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ?? "ws://localhost:8000";
export const USE_MOCK =
  (import.meta.env.VITE_USE_MOCK as string | undefined) === "true";

const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Add auth interceptor - attach JWT token from session to all requests
http.interceptors.request.use((config) => {
  if (!USE_MOCK) {
    const session = getSession();
    if (session?.token) {
      config.headers.Authorization = `Bearer ${session.token}`;
    }
  }
  return config;
});

// Handle 401 errors - attempt token refresh before redirecting
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !USE_MOCK) {
      const originalRequest = error.config;
      
      // Prevent infinite retry loop
      if (!originalRequest._retry) {
        originalRequest._retry = true;
        
        try {
          // Attempt to refresh the token
          const newToken = await refreshToken();
          
          if (newToken) {
            // Update authorization header and retry
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return http(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, clear session and redirect
          localStorage.removeItem("mp.session.v1");
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
      
      // Refresh already attempted or failed, redirect to login
      localStorage.removeItem("mp.session.v1");
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

function delay<T>(v: T, ms = 120): Promise<T> {
  return new Promise((res) => setTimeout(() => res(v), ms));
}
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

const store = {
  accounts: clone(mock.mockAccounts),
  channels: clone(mock.mockChannels),
  profiles: clone(mock.mockRiskProfiles),
  trades: clone(mock.mockActiveTrades),
  history: clone(mock.mockTradeHistory),
  notifications: clone(mock.mockNotifications),
  bot: clone(mock.mockBotStatus),
};

// ─────────────────────────── Accounts (8) ─────────────────────────────
export const accountsApi = {
  list: () =>
    USE_MOCK ? delay(store.accounts) : http.get<Account[]>("/api/accounts/").then(r => r.data),
  get: (key: string) =>
    USE_MOCK
      ? delay(store.accounts.find(a => a.account_key === key)!)
      : http.get<Account>(`/api/accounts/${encodeURIComponent(key)}`).then(r => r.data),
  create: (body: Record<string, unknown>) =>
    USE_MOCK
      ? delay({ ...store.accounts[0], ...body } as Account)
      : http.post<Account>("/api/accounts/", body).then(r => r.data),
  update: (key: string, body: Partial<Account>) =>
    USE_MOCK
      ? delay(((store.accounts = store.accounts.map(a => a.account_key === key ? { ...a, ...body } : a)), store.accounts.find(a => a.account_key === key)!))
      : http.put<Account>(`/api/accounts/${encodeURIComponent(key)}`, body).then(r => r.data),
  delete: (key: string) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.accounts = store.accounts.filter(a => a.account_key !== key); return r; })
      : http.delete<{ success: boolean }>(`/api/accounts/${encodeURIComponent(key)}`).then(r => r.data),
  pause: (key: string) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.accounts = store.accounts.map(a => a.account_key === key ? { ...a, paused: true } : a); return r; })
      : http.post<{ success: boolean }>(`/api/accounts/${encodeURIComponent(key)}/pause`, {}).then(r => r.data),
  resume: (key: string) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.accounts = store.accounts.map(a => a.account_key === key ? { ...a, paused: false } : a); return r; })
      : http.post<{ success: boolean }>(`/api/accounts/${encodeURIComponent(key)}/resume`, {}).then(r => r.data),
  updateProfitCap: (key: string, body: { enabled: boolean; cap_type?: string; cap_value?: number; buffer_pct?: number }) =>
    USE_MOCK
      ? delay(store.accounts.find(a => a.account_key === key)!)
      : http.post<Account>(`/api/accounts/${encodeURIComponent(key)}/profit-cap`, body).then(r => r.data),
  unfreezeProfitCap: (key: string) =>
    USE_MOCK
      ? delay(((store.accounts = store.accounts.map(a => a.account_key === key ? { ...a, profit_cap_frozen: false } : a)), store.accounts.find(a => a.account_key === key)!))
      : http.post<Account>(`/api/accounts/${encodeURIComponent(key)}/unfreeze-profit-cap`, {}).then(r => r.data),
  discover: (body: { email: string; password: string; server: string; prop_firm: string }) =>
    USE_MOCK
      ? delay({ accounts: [{ id: "123456", number: "ACC-001", balance: 10000 }, { id: "789012", number: "ACC-002", balance: 5000 }] })
      : http.post<{ accounts: { id: string; number: string; balance: number }[] }>("/api/accounts/discover", body).then(r => r.data),
};

// ─────────────────────────── Channels (8) ─────────────────────────────
export const channelsApi = {
  list: () => USE_MOCK ? delay(store.channels) : http.get<Channel[]>("/api/channels/").then(r => r.data),
  get: (id: number) =>
    USE_MOCK
      ? delay(store.channels.find(c => c.channel_id === id)!)
      : http.get<Channel>(`/api/channels/${id}`).then(r => r.data),
  create: (body: Channel) =>
    USE_MOCK
      ? delay(((store.channels = [...store.channels, body]), body))
      : http.post<Channel>("/api/channels/", body).then(r => r.data),
  update: (id: number, body: Channel) =>
    USE_MOCK
      ? delay(((store.channels = store.channels.map(c => c.channel_id === id ? body : c)), body))
      : http.put<Channel>(`/api/channels/${id}`, body).then(r => r.data),
  patch: (id: number, body: Partial<Channel>) =>
    USE_MOCK
      ? delay(((store.channels = store.channels.map(c => c.channel_id === id ? { ...c, ...body } : c)), store.channels.find(c => c.channel_id === id)!))
      : http.patch<Channel>(`/api/channels/${id}`, body).then(r => r.data),
  delete: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.channels = store.channels.filter(c => c.channel_id !== id); return r; })
      : http.delete<{ success: boolean }>(`/api/channels/${id}`).then(r => r.data),
  enable: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.channels = store.channels.map(c => c.channel_id === id ? { ...c, enabled: true } : c); return r; })
      : http.post<{ success: boolean }>(`/api/channels/${id}/enable`, {}).then(r => r.data),
  disable: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.channels = store.channels.map(c => c.channel_id === id ? { ...c, enabled: false } : c); return r; })
      : http.post<{ success: boolean }>(`/api/channels/${id}/disable`, {}).then(r => r.data),
};

// ─────────────────────────── Risk Profiles (7) ────────────────────────
export const riskProfilesApi = {
  list: () => USE_MOCK ? delay(store.profiles) : http.get<RiskProfile[]>("/api/risk-profiles/").then(r => r.data),
  get: (id: number) =>
    USE_MOCK
      ? delay(store.profiles.find(p => p.profile_id === id)!)
      : http.get<RiskProfile>(`/api/risk-profiles/${id}`).then(r => r.data),
  getDefault: () =>
    USE_MOCK
      ? delay(store.profiles.find(p => p.is_default)!)
      : http.get<RiskProfile>("/api/risk-profiles/default").then(r => r.data),
  create: (body: Omit<RiskProfile, "profile_id">) =>
    USE_MOCK
      ? delay({ ...body, profile_id: Math.max(0, ...store.profiles.map(p => p.profile_id)) + 1 } as RiskProfile)
          .then(p => { store.profiles = [...store.profiles, p]; return p; })
      : http.post<RiskProfile>("/api/risk-profiles/", body).then(r => r.data),
  update: (id: number, body: RiskProfile) =>
    USE_MOCK
      ? delay(((store.profiles = store.profiles.map(p => p.profile_id === id ? body : p)), body))
      : http.put<RiskProfile>(`/api/risk-profiles/${id}`, body).then(r => r.data),
  patch: (id: number, body: Partial<RiskProfile>) =>
    USE_MOCK
      ? delay(((store.profiles = store.profiles.map(p => p.profile_id === id ? { ...p, ...body } : p)), store.profiles.find(p => p.profile_id === id)!))
      : http.patch<RiskProfile>(`/api/risk-profiles/${id}`, body).then(r => r.data),
  delete: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.profiles = store.profiles.filter(p => p.profile_id !== id); return r; })
      : http.delete<{ success: boolean }>(`/api/risk-profiles/${id}`).then(r => r.data),
};

// ─────────────────────────── Trades (7) ───────────────────────────────
export const tradesApi = {
  activeAll: () =>
    USE_MOCK ? delay(store.trades) : http.get<ActiveTrade[]>("/api/trades/active").then(r => r.data),
  activeByAccount: (k: string) =>
    USE_MOCK
      ? delay(store.trades.filter(t => t.account_key === k))
      : http.get<ActiveTrade[]>(`/api/trades/active/${encodeURIComponent(k)}`).then(r => r.data),
  close: (id: number) =>
    USE_MOCK
      ? delay({ success: true, message: `Closed trade ${id}` }).then(r => { store.trades = store.trades.filter(t => t.trade_id !== id); return r; })
      : http.post<{ success: boolean; message: string }>(`/api/trades/active/${id}/close`, { action_type: "MANUAL_CLOSE", reason: "User initiated close" }).then(r => r.data),
  breakeven: (id: number) =>
    USE_MOCK
      ? delay({ success: true, message: `Breakeven set on ${id}` }).then(r => { store.trades = store.trades.map(t => t.trade_id === id ? { ...t, sl: t.entry_price } : t); return r; })
      : http.post<{ success: boolean; message: string }>(`/api/trades/active/${id}/breakeven`, { action_type: "MANUAL_BE", reason: "User set breakeven" }).then(r => r.data),
  partial: (id: number, percentage: 25 | 50 | 75) =>
    USE_MOCK
      ? delay({ success: true, message: `Closed ${percentage}% of ${id}`, remaining_lots: 0 }).then(r => {
          let remaining = 0;
          store.trades = store.trades.map(t => {
            if (t.trade_id !== id) return t;
            const newLots = +(t.lot_size * (1 - percentage / 100)).toFixed(2);
            remaining = newLots;
            return { ...t, lot_size: newLots };
          });
          return { ...r, remaining_lots: remaining };
        })
      : http.post<{ success: boolean; message: string; remaining_lots: number }>(`/api/trades/active/${id}/partial`, { action_type: `MANUAL_PARTIAL_${percentage}`, reason: `User closed ${percentage}%`, percentage }).then(r => r.data),
  history: (params: { account_key?: string; limit?: number; offset?: number } = {}) =>
    USE_MOCK
      ? delay({
          trades: store.history.filter(t => !params.account_key || t.account_key === params.account_key)
            .slice(params.offset ?? 0, (params.offset ?? 0) + (params.limit ?? 50)),
          total: store.history.filter(t => !params.account_key || t.account_key === params.account_key).length,
        })
      : http.get<TradeHistory[]>("/api/trades/history", { params }).then(r => ({ trades: r.data, total: r.data.length })),
  historyAll: (params: { account_key?: string } = {}) =>
    USE_MOCK
      ? delay(store.history.filter(t => !params.account_key || t.account_key === params.account_key))
      : http.get<TradeHistory[]>("/api/trades/history", { params: { ...params, limit: 5000, offset: 0 } }).then(r => r.data),
  exportCsvBlob: async (accountKey?: string): Promise<Blob> => {
    if (USE_MOCK) {
      const rows = store.history.filter(t => !accountKey || t.account_key === accountKey);
      const header = "history_id,account_key,channel_name,symbol,direction,entry_price,exit_price,lot_size,entry_time,exit_time,pnl,outcome,close_reason,manual_action_type\n";
      const body = rows.map(t => [
        t.history_id, t.account_key, t.channel_name, t.symbol, t.direction,
        t.entry_price, t.exit_price, t.lot_size, t.entry_time, t.exit_time,
        t.pnl, t.outcome, t.close_reason, t.manual_action_type ?? "",
      ].join(",")).join("\n");
      return new Blob([header + body], { type: "text/csv" });
    }
    const res = await http.get(`/api/trades/history/export`, {
      params: accountKey ? { account_key: accountKey } : undefined,
      responseType: "blob",
    });
    return res.data as Blob;
  },
};

// ─────────────────────────── Notifications (5) ────────────────────────
export const notificationsApi = {
  list: (params: { unread_only?: boolean; limit?: number } = {}) =>
    USE_MOCK
      ? delay(store.notifications.filter(n => !params.unread_only || !n.read).slice(0, params.limit ?? 50))
      : http.get<Notification[]>("/api/notifications/", { params }).then(r => r.data),
  create: (body: Omit<Notification, "notification_id" | "created_at" | "read">) =>
    USE_MOCK
      ? delay({ ...body, notification_id: Date.now(), created_at: new Date().toISOString(), read: false } as Notification)
          .then(n => { store.notifications = [n, ...store.notifications]; return n; })
      : http.post<Notification>("/api/notifications/", body).then(r => r.data),
  markRead: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.notifications = store.notifications.map(n => n.notification_id === id ? { ...n, read: true } : n); return r; })
      : http.patch<{ success: boolean }>(`/api/notifications/${id}/read`, {}).then(r => r.data),
  markAllRead: () =>
    USE_MOCK
      ? delay({ success: true, count: store.notifications.filter(n => !n.read).length })
          .then(r => { store.notifications = store.notifications.map(n => ({ ...n, read: true })); return r; })
      : http.post<{ success: boolean; count: number }>("/api/notifications/mark-all-read", {}).then(r => r.data),
  delete: (id: number) =>
    USE_MOCK
      ? delay({ success: true }).then(r => { store.notifications = store.notifications.filter(n => n.notification_id !== id); return r; })
      : http.delete<{ success: boolean }>(`/api/notifications/${id}`).then(r => r.data),
};

// ─────────────────────────── Bot (4) ─────────────────────────────────
export const botApi = {
  status: () => USE_MOCK ? delay(store.bot) : http.get<BotStatus>("/api/bot/status").then(r => r.data),
  control: (action: "start" | "stop") =>
    USE_MOCK
      ? delay({ success: true, status: action === "start" ? "running" : "stopped" })
          .then(r => { store.bot = { ...store.bot, status: r.status }; return r; })
      : http.post<{ success: boolean; status: string }>("/api/bot/control", { action }).then(r => r.data),
  forceCloseAll: () =>
    USE_MOCK
      ? delay({ success: true, closed_count: store.trades.length })
          .then(r => { store.trades = []; store.bot = { ...store.bot, total_active_trades: 0 }; return r; })
      : http.post<{ success: boolean; closed_count: number }>("/api/bot/force-close-all", {}).then(r => r.data),
  forceCloseAccount: (key: string) =>
    USE_MOCK
      ? delay({ success: true, closed_count: store.trades.filter(t => t.account_key === key).length })
          .then(r => { store.trades = store.trades.filter(t => t.account_key !== key); store.bot = { ...store.bot, total_active_trades: store.trades.length }; return r; })
      : http.post<{ success: boolean; closed_count: number }>(`/api/bot/force-close-account/${encodeURIComponent(key)}`, {}).then(r => r.data),
};

// ─────────────────────────── Users (4) ────────────────────────────────
export const usersApi = {
  me: () => http.get<User>("/api/users/me").then(r => r.data),
  pending: () => http.get<User[]>("/api/users/pending").then(r => r.data),
  all: () => http.get<User[]>("/api/users/all").then(r => r.data),
  approve: (userId: string) => http.post<{ success: boolean; message: string }>(`/api/users/${userId}/approve`).then(r => r.data),
};

export const QK = {
  accounts: ["accounts"] as const,
  channels: ["channels"] as const,
  profiles: ["risk-profiles"] as const,
  activeTrades: ["active-trades"] as const,
  tradeHistory: (accountKey?: string) => ["trade-history", accountKey ?? "all"] as const,
  notifications: (unreadOnly: boolean) => ["notifications", unreadOnly] as const,
  botStatus: ["bot-status"] as const,
  pendingUsers: ["pending-users"] as const,
  allUsers: ["all-users"] as const,
};