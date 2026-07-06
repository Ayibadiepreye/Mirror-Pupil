# Web Frontend Profit Cap Integration Guide

## ✅ COMPLETED

1. **TypeScript Types** - Added profit cap fields to Account interface
   - File: `src/lib/mp/types.ts`
   - Fields: `profit_cap_enabled`, `profit_cap_type`, `profit_cap_value`, `profit_cap_buffer_pct`, `profit_cap_frozen`

2. **API Client** - Added profit cap endpoints
   - File: `src/lib/mp/api.ts`
   - Methods: `updateProfitCap()`, `unfreezeProfitCap()`

3. **Profit Cap Component** - Created reusable component
   - File: `src/components/mp/ProfitCapSection.tsx`
   - Features: Enable/disable toggle, cap type selector, value input, buffer input, unfreeze button

## 🔧 INTEGRATION STEPS

### Step 1: Add Profit Cap Status Indicator to Account Card

In `src/components/mp/pages/AccountsPage.tsx`, update the status badges section:

```tsx
// Find this section (around line 179):
{!a.paused && !a.breached && (
  <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-success)]/15 text-[color:var(--mp-success)] uppercase font-semibold">
    <ShieldCheck className="size-3" /> Active
  </span>
)}

// ADD THIS AFTER the Active badge (before closing div):
{a.profit_cap_frozen && (
  <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-danger)] text-white uppercase font-semibold ml-1">
    <Lock className="size-3" /> CAP FROZEN
  </span>
)}
{a.profit_cap_enabled && !a.profit_cap_frozen && (
  <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[color:var(--mp-primary)]/15 text-[color:var(--mp-primary)] uppercase font-semibold ml-1">
    <Shield className="size-3" /> CAP ACTIVE
  </span>
)}
```

**Required imports at top of file:**
```tsx
import { Lock, Shield } from "lucide-react"; // Add Lock and Shield
```

### Step 2: Add Profit Cap Info Box to Account Card

In the same file, after the drawdown progress bars, add:

```tsx
// After Max Drawdown progress bar (around line 213), ADD:
{/* Profit Cap Info */}
{a.profit_cap_enabled && (
  <div className="mt-3 p-2 rounded-md bg-[color:var(--mp-primary)]/10 border border-[color:var(--mp-primary)]">
    <div className="flex items-center gap-2">
      {a.profit_cap_frozen ? (
        <Lock className="size-3 text-[color:var(--mp-danger)]" />
      ) : (
        <Shield className="size-3 text-[color:var(--mp-primary)]" />
      )}
      <span className="text-xs font-semibold">
        {a.profit_cap_frozen 
          ? "Profit Cap FROZEN" 
          : `Profit Cap: ${a.profit_cap_type === "percentage" ? `${a.profit_cap_value}%` : `$${a.profit_cap_value}`}`
        }
      </span>
    </div>
  </div>
)}
```

### Step 3: Add Profit Cap Section to Edit Dialog

Find the EditAccountDialog component in the same file (or wherever it's defined), and add:

```tsx
// Import the component at the top:
import { ProfitCapSection } from "@/components/mp/ProfitCapSection";

// Inside the Dialog content, after the risk profile section, ADD:
<div className="pt-4 border-t">
  <ProfitCapSection 
    account={editing} 
    onSuccess={() => setEditing(null)} 
  />
</div>
```

### Step 4: Update Mock Data (Optional, for development)

In `src/lib/mp/mock-data.ts`, add profit cap fields to mock accounts:

```typescript
// Add to each mock account object:
profit_cap_enabled: false,
profit_cap_type: null,
profit_cap_value: null,
profit_cap_buffer_pct: 2.0,
profit_cap_frozen: false,
```

---

## 🎨 VISUAL EXAMPLE

After integration, your account card will show:

```
┌─────────────────────────────────────────────┐
│ Account Name    [ACTIVE] [CAP ACTIVE]       │
│ user@email.com:12345                        │
│ live                                        │
│                                             │
│ $5,150                 +$65 today           │
│                                             │
│ Initial: $5,000  Profile: Default  Lot: 0.1│
│                                             │
│ Daily Drawdown: 1.2% / 3%                   │
│ ████░░░░░░░░░░░░░░                         │
│                                             │
│ Max Drawdown: 2.5% / 6%                     │
│ ████████░░░░░░░░░░░░                       │
│                                             │
│ 🛡️ Profit Cap: $250                         │
│                                             │
│ [Pause] [Edit] [Delete]                    │
└─────────────────────────────────────────────┘
```

**When Frozen:**
```
┌─────────────────────────────────────────────┐
│ Account Name    [BREACHED] [CAP FROZEN]     │
│ ...                                         │
│ 🔒 Profit Cap FROZEN                        │
└─────────────────────────────────────────────┘
```

**Edit Dialog:**
```
┌─────────────────────────────────────────────┐
│ Edit Account                                │
│                                             │
│ Display Name: [___________________]         │
│ Lot Size: [___________________]            │
│ Risk Profile: [Default          ▼]         │
│                                             │
│ ─────────────────────────────────────       │
│                                             │
│ 🛡️ Profit Cap                               │
│                                             │
│ ⚠️ Account frozen due to profit cap breach │
│    All trades closed. Unfreeze to resume.  │
│    [Unfreeze Account]                       │
│                                             │
│ Enable Profit Cap  [ON ✓]                  │
│                                             │
│ Cap Type: [Dollar Amount      ▼]           │
│ Cap Value: [214              $]             │
│ Safety Buffer (%): [2        %]             │
│                                             │
│ [Save Profit Cap]                           │
│                                             │
│ [Cancel]  [Save]                            │
└─────────────────────────────────────────────┘
```

---

## 📝 TESTING

1. Start development server: `npm run dev`
2. Navigate to Accounts page
3. Click "Edit" on an account
4. Scroll down to "Profit Cap" section
5. Toggle enable, configure settings
6. Click "Save Profit Cap"
7. Verify status badges update on card
8. Verify profit cap info box appears

---

## 🚀 DEPLOYMENT

Once integration is complete:

1. Build production: `npm run build`
2. Deploy to hosting (Vercel/Netlify/etc.)
3. Ensure `VITE_API_URL` points to your VPS backend
4. Test end-to-end with real accounts

---

## ✅ CHECKLIST

- [ ] Import Lock and Shield icons in AccountsPage.tsx
- [ ] Add status badges (CAP FROZEN / CAP ACTIVE)
- [ ] Add profit cap info box to card
- [ ] Import ProfitCapSection component
- [ ] Add ProfitCapSection to Edit Dialog
- [ ] Update mock data (optional)
- [ ] Test in development
- [ ] Build and deploy to production

---

**All TypeScript types, API client methods, and the profit cap component are ready. Just follow the integration steps above!**
