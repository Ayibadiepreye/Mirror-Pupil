import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useRouter } from "@tanstack/react-router";
import {
  AlertCircle, AlertTriangle, CheckCheck, ChevronDown, ChevronUp, Info, Mail, Trash2, Zap, X,
} from "lucide-react";
import { notificationsApi, QK } from "@/lib/mp/api";
import { formatTimeAgo, shortenKey } from "@/lib/mp/utils";
import { useMirrorPupilWebSocket } from "@/lib/mp/ws";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import type { Notification, NotificationCategory, NotificationSeverity } from "@/lib/mp/types";

const CAT_ICON: Record<NotificationCategory, React.ComponentType<{ className?: string }>> = {
  SIGNAL: Zap, EXECUTION: CheckCheck, MANAGEMENT: Info, BREACH: AlertTriangle, SYSTEM: AlertCircle,
};
const SEV_BORDER: Record<NotificationSeverity, string> = {
  CRITICAL: "border-l-[color:var(--mp-danger)]",
  ERROR: "border-l-[color:var(--mp-warning)]",
  WARNING: "border-l-[color:var(--mp-warning)]",
  INFO: "border-l-[color:var(--mp-info)]",
};
const SEV_BADGE: Record<NotificationSeverity, string> = {
  CRITICAL: "bg-[color:var(--mp-danger)]/15 text-[color:var(--mp-danger)]",
  ERROR: "bg-[color:var(--mp-warning)]/15 text-[color:var(--mp-warning)]",
  WARNING: "bg-[color:var(--mp-warning)]/15 text-[color:var(--mp-warning)]",
  INFO: "bg-[color:var(--mp-info)]/15 text-[color:var(--mp-info)]",
};

export function NotificationsPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const ws = useMirrorPupilWebSocket();
  const navigate = useNavigate();
  const router = useRouter();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const listQ = useQuery({
    queryKey: QK.notifications(unreadOnly),
    queryFn: () => notificationsApi.list({ unread_only: unreadOnly, limit: 200 }),
    refetchInterval: ws === "connected" ? 30_000 : 5_000,
  });

  const items = listQ.data ?? [];
  const criticals = useMemo(() => items.filter((n) => n.severity === "CRITICAL" && !n.read), [items]);
  const unreadCount = items.filter((n) => !n.read).length;

  const markReadM = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAllM = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["notifications"] }); toast.success(`Marked ${r.count} as read`); },
  });
  const deleteM = useMutation({
    mutationFn: (id: number) => notificationsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notifications"] }); toast.success("Notification deleted"); },
  });

  const onDelete = async (n: Notification) => {
    const ok = await confirm({
      title: "Delete this notification?",
      description: n.title,
      destructive: true, confirmLabel: "Delete",
    });
    if (ok) deleteM.mutate(n.notification_id);
  };

  const close = () => {
    // Prefer back-nav if we have somewhere to return to, else go to dashboard.
    const canGoBack =
      typeof window !== "undefined" && window.history.length > 1;
    if (canGoBack) router.history.back();
    else navigate({ to: "/" });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={close}
            aria-label="Close notifications"
            className="mt-0.5 size-8 rounded-full border border-[color:var(--mp-border)] hover:bg-white/5"
          >
            <X className="size-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
            <p className="text-sm text-[color:var(--mp-text-dim)]">
              <span className="font-mono">{unreadCount}</span> unread of {items.length}.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Switch id="unread-only" checked={unreadOnly} onCheckedChange={setUnreadOnly} />
            <Label htmlFor="unread-only" className="text-xs uppercase tracking-wider">Unread only</Label>
          </div>
          <Button onClick={() => markAllM.mutate()} disabled={unreadCount === 0 || markAllM.isPending} className="gap-1.5 bg-[color:var(--mp-crimson)] hover:bg-[color:var(--mp-crimson)]/90 text-white">
            <CheckCheck className="size-4" /> Mark all read
          </Button>
        </div>
      </div>

      {criticals.length > 0 && (
        <section className="rounded-lg border border-[color:var(--mp-danger)]/40 bg-gradient-to-br from-[color:var(--mp-danger)]/30 via-[color:var(--mp-crimson)]/20 to-transparent p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="size-5 text-[color:var(--mp-danger)]" />
            <h2 className="font-semibold">Critical alerts</h2>
          </div>
          <ul className="space-y-1.5">
            {criticals.map((n) => (
              <li key={n.notification_id} className="flex items-start justify-between gap-2 text-sm">
                <div>
                  <span className="font-semibold">{n.title}</span> —{" "}
                  <span className="text-[color:var(--mp-text-dim)]">{n.message}</span>
                </div>
                <button onClick={() => markReadM.mutate(n.notification_id)} className="text-[11px] uppercase tracking-wider text-[color:var(--mp-text-dim)] hover:text-white">
                  Dismiss
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ul className="space-y-2">
        {items.length === 0 && (
          <li className="p-10 text-center text-[color:var(--mp-text-dim)] text-sm border border-dashed border-[color:var(--mp-border)] rounded-lg">
            No notifications.
          </li>
        )}
        {items.map((n) => {
          const Icon = CAT_ICON[n.category];
          const open = expanded === n.notification_id;
          return (
            <li
              key={n.notification_id}
              className={`relative rounded-lg border border-[color:var(--mp-border)] ${SEV_BORDER[n.severity]} border-l-4 bg-[color:var(--mp-base)] p-3`}
            >
              <div className="flex items-start gap-3">
                <Icon className="size-4 mt-0.5 text-[color:var(--mp-text-dim)] shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      {!n.read && <span className="size-1.5 rounded-full bg-[color:var(--mp-red)] shrink-0" aria-label="unread" />}
                      <h3 className="font-semibold text-sm truncate">{n.title}</h3>
                    </div>
                    <span className="text-[11px] text-[color:var(--mp-text-dim)] shrink-0">{formatTimeAgo(n.created_at)}</span>
                  </div>
                  <p className="text-xs text-[color:var(--mp-text)] mt-0.5">{n.message}</p>
                  <div className="flex items-center flex-wrap gap-1.5 mt-2">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${SEV_BADGE[n.severity]}`}>{n.severity}</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/5 text-[color:var(--mp-text-dim)]">{n.category}</span>
                    {n.account_key && (
                      <span className="text-[10px] font-mono text-[color:var(--mp-text-dim)]">{shortenKey(n.account_key)}</span>
                    )}
                    {!!n.metadata && typeof n.metadata === "object" && Object.keys(n.metadata as object).length > 0 && (
                      <button
                        onClick={() => setExpanded(open ? null : n.notification_id)}
                        className="text-[10px] inline-flex items-center gap-0.5 text-[color:var(--mp-text-dim)] hover:text-white"
                      >
                        {open ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                        metadata
                      </button>
                    )}
                  </div>
                  {open && (
                    <pre className="mt-2 p-2 text-[11px] font-mono bg-black/30 rounded overflow-x-auto">
                      {String(JSON.stringify(n.metadata, null, 2))}
                    </pre>
                  )}
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  {!n.read && (
                    <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs" onClick={() => markReadM.mutate(n.notification_id)}>
                      <Mail className="size-3" /> Read
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs text-[color:var(--mp-danger)] hover:text-[color:var(--mp-danger)]" onClick={() => onDelete(n)}>
                    <Trash2 className="size-3" /> Delete
                  </Button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}