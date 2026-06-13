import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, Shield, User as UserIcon } from "lucide-react";
import { QK, usersApi } from "@/lib/mp/api";
import { formatTimeAgo } from "@/lib/mp/utils";
import { useConfirm } from "@/components/mp/ConfirmDialog";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { User } from "@/lib/mp/types";

export function UsersPage() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [showPendingOnly, setShowPendingOnly] = useState(true);

  const pendingQ = useQuery({
    queryKey: QK.pendingUsers,
    queryFn: usersApi.pending,
  });

  const allQ = useQuery({
    queryKey: QK.allUsers,
    queryFn: usersApi.all,
  });

  const approveM = useMutation({
    mutationFn: (userId: string) => usersApi.approve(userId),
    onSuccess: (r) => {
      toast.success(r.message ?? "User approved");
      qc.invalidateQueries({ queryKey: QK.pendingUsers });
      qc.invalidateQueries({ queryKey: QK.allUsers });
    },
    onError: () => toast.error("Failed to approve user"),
  });

  const doApprove = async (u: User) => {
    const ok = await confirm({
      title: `Approve user ${u.email}?`,
      description: "This will grant them access to the system.",
      confirmLabel: "Approve",
    });
    if (ok) approveM.mutate(u.user_id);
  };

  const users = showPendingOnly ? pendingQ.data ?? [] : allQ.data ?? [];
  const isLoading = showPendingOnly ? pendingQ.isLoading : allQ.isLoading;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">User Management</h1>
          <p className="text-sm text-[color:var(--mp-text-dim)]">Approve and manage system users.</p>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          variant={showPendingOnly ? "default" : "outline"}
          size="sm"
          className="gap-1.5"
          onClick={() => setShowPendingOnly(true)}
        >
          <Clock className="size-3.5" /> Pending Approval
        </Button>
        <Button
          variant={!showPendingOnly ? "default" : "outline"}
          size="sm"
          className="gap-1.5"
          onClick={() => setShowPendingOnly(false)}
        >
          <UserIcon className="size-3.5" /> All Users
        </Button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--mp-accent)]"></div>
        </div>
      ) : users.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-[color:var(--mp-border)] rounded-lg">
          <p className="text-[color:var(--mp-text-dim)] text-sm">
            {showPendingOnly ? "No pending users." : "No users found."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {users.map((u) => (
            <article
              key={u.user_id}
              className="relative rounded-lg border border-[color:var(--mp-border)] bg-[color:var(--mp-base)] overflow-hidden"
            >
              <div className="relative p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm truncate">{u.email}</h3>
                    {u.display_name && (
                      <p className="text-xs text-[color:var(--mp-text-dim)] truncate">{u.display_name}</p>
                    )}
                  </div>
                  <div className="flex flex-col gap-1.5 items-end flex-shrink-0">
                    {u.is_super_admin && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[color:var(--mp-crimson)]/20 text-[color:var(--mp-text)] uppercase">
                        <Shield className="size-3" /> Admin
                      </span>
                    )}
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        u.is_approved
                          ? "bg-[color:var(--mp-success)]/20 text-[color:var(--mp-success)]"
                          : "bg-orange-500/20 text-orange-500"
                      }`}
                    >
                      {u.is_approved ? (
                        <>
                          <CheckCircle2 className="size-3" /> Approved
                        </>
                      ) : (
                        <>
                          <Clock className="size-3" /> Pending
                        </>
                      )}
                    </span>
                  </div>
                </div>

                <div className="text-[11px] text-[color:var(--mp-text-dim)]">
                  Registered {formatTimeAgo(u.created_at)}
                </div>

                {!u.is_approved && (
                  <Button
                    size="sm"
                    className="w-full gap-1.5"
                    onClick={() => doApprove(u)}
                    disabled={approveM.isPending}
                  >
                    <CheckCircle2 className="size-3.5" /> Approve User
                  </Button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
