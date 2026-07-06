/**
 * Profit Cap Configuration Section Component
 * Used in Edit Account Dialog to configure profit cap settings
 */
import { useState } from "react";
import { Lock, Shield, AlertTriangle } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { accountsApi, QK } from "@/lib/mp/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { Account } from "@/lib/mp/types";

interface ProfitCapSectionProps {
  account: Account;
  onSuccess?: () => void;
}

export function ProfitCapSection({ account, onSuccess }: ProfitCapSectionProps) {
  const qc = useQueryClient();
  const [enabled, setEnabled] = useState(account.profit_cap_enabled);
  const [capType, setCapType] = useState(account.profit_cap_type ?? "dollar");
  const [capValue, setCapValue] = useState(account.profit_cap_value?.toString() ?? "0");
  const [buffer, setBuffer] = useState(account.profit_cap_buffer_pct.toString());

  const updateCapM = useMutation({
    mutationFn: () => accountsApi.updateProfitCap(account.account_key, {
      enabled,
      cap_type: capType,
      cap_value: parseFloat(capValue),
      buffer_pct: parseFloat(buffer),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.accounts });
      toast.success("Profit cap updated successfully");
      onSuccess?.();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "Failed to update profit cap");
    },
  });

  const unfreezeM = useMutation({
    mutationFn: () => accountsApi.unfreezeProfitCap(account.account_key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.accounts });
      toast.success("Account unfrozen successfully");
      onSuccess?.();
    },
    onError: () => toast.error("Failed to unfreeze account"),
  });

  const handleSave = () => {
    // Validation
    if (enabled) {
      const val = parseFloat(capValue);
      const buf = parseFloat(buffer);
      
      if (isNaN(val) || val <= 0) {
        toast.error("Cap value must be greater than 0");
        return;
      }
      
      if (isNaN(buf) || buf < 0 || buf > 100) {
        toast.error("Buffer must be between 0 and 100");
        return;
      }
    }
    
    updateCapM.mutate();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <Shield className="size-4" />
          Profit Cap
          {account.profit_cap_frozen && (
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-danger)] text-white uppercase font-semibold">
              <Lock className="size-3" /> FROZEN
            </span>
          )}
        </h3>
      </div>

      {/* Frozen Warning */}
      {account.profit_cap_frozen && (
        <div className="p-3 bg-[color:var(--mp-danger)]/10 border border-[color:var(--mp-danger)] rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="size-4 text-[color:var(--mp-danger)] mt-0.5 shrink-0" />
            <div className="space-y-2 flex-1">
              <p className="text-sm font-semibold text-[color:var(--mp-danger)]">
                Account frozen due to profit cap breach
              </p>
              <p className="text-xs text-[color:var(--mp-text-dim)]">
                All trades have been closed. Unfreeze to resume trading.
              </p>
              <Button
                size="sm"
                onClick={() => unfreezeM.mutate()}
                disabled={unfreezeM.isPending}
                className="bg-[color:var(--mp-success)] hover:bg-[color:var(--mp-success)]/90 text-white"
              >
                {unfreezeM.isPending ? "Unfreezing..." : "Unfreeze Account"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Enable Toggle */}
      <div className="flex items-center justify-between">
        <Label htmlFor="profit-cap-enabled" className="text-sm font-medium">
          Enable Profit Cap
        </Label>
        <Switch
          id="profit-cap-enabled"
          checked={enabled}
          onCheckedChange={setEnabled}
        />
      </div>

      {/* Cap Configuration (only show when enabled) */}
      {enabled && (
        <div className="space-y-3 pt-2">
          {/* Cap Type */}
          <div className="space-y-1.5">
            <Label htmlFor="cap-type" className="text-xs">Cap Type</Label>
            <Select value={capType} onValueChange={setCapType}>
              <SelectTrigger id="cap-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dollar">Dollar Amount</SelectItem>
                <SelectItem value="percentage">Percentage</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Cap Value */}
          <div className="space-y-1.5">
            <Label htmlFor="cap-value" className="text-xs">
              Cap Value
            </Label>
            <div className="relative">
              <Input
                id="cap-value"
                type="number"
                step="0.01"
                value={capValue}
                onChange={(e) => setCapValue(e.target.value)}
                className="pr-8"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-[color:var(--mp-text-dim)]">
                {capType === "percentage" ? "%" : "$"}
              </span>
            </div>
            <p className="text-xs text-[color:var(--mp-text-dim)]">
              {capType === "percentage"
                ? "e.g., 5 = 5% profit cap"
                : "e.g., 250 = $250 profit cap"}
            </p>
          </div>

          {/* Safety Buffer */}
          <div className="space-y-1.5">
            <Label htmlFor="buffer" className="text-xs">
              Safety Buffer (%)
            </Label>
            <div className="relative">
              <Input
                id="buffer"
                type="number"
                step="0.1"
                value={buffer}
                onChange={(e) => setBuffer(e.target.value)}
                className="pr-8"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-[color:var(--mp-text-dim)]">
                %
              </span>
            </div>
            <p className="text-xs text-[color:var(--mp-text-dim)]">
              Triggers before exact cap (default: 2%)
            </p>
          </div>

          {/* Save Button */}
          <Button
            onClick={handleSave}
            disabled={updateCapM.isPending}
            className="w-full bg-[color:var(--mp-primary)] hover:bg-[color:var(--mp-primary)]/90"
          >
            {updateCapM.isPending ? "Saving..." : "Save Profit Cap"}
          </Button>
        </div>
      )}
    </div>
  );
}
