import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginWithGoogle, loginWithEmail, registerWithEmail } from "@/lib/firebase";
import { usersApi } from "@/lib/mp/api";
import logoUrl from "@/assets/logo.svg";

export function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onGoogle = async () => {
    setBusy(true);
    try {
      await loginWithGoogle();
      
      // Create/fetch user record from backend
      try {
        const userData = await usersApi.me();
        if (!userData.is_approved) {
          toast.warning("Account pending admin approval");
          // Still allow navigation to show pending message
        } else {
          toast.success("Signed in with Google");
        }
      } catch (error: any) {
        if (error.response?.status === 403) {
          toast.warning("Account pending admin approval");
        }
      }
      
      navigate({ to: "/" });
    } catch (e: any) {
      toast.error(e.message || "Google sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  const onPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "signup") {
        await registerWithEmail(email, password);
        toast.success("Account created! Pending admin approval.");
      } else {
        await loginWithEmail(email, password);
        
        // Check approval status
        try {
          const userData = await usersApi.me();
          if (!userData.is_approved) {
            toast.warning("Account pending admin approval");
          } else {
            toast.success("Signed in successfully");
          }
        } catch (error: any) {
          if (error.response?.status === 403) {
            toast.warning("Account pending admin approval");
          }
        }
      }
      
      navigate({ to: "/" });
    } catch (err: any) {
      toast.error(err.message || "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-[color:var(--mp-app)] text-[color:var(--mp-text)] p-4 relative overflow-hidden">
      {/* Backdrop glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-50 login-backdrop-glow"
      />

      <div className="relative w-full max-w-md">
        <div className="text-center mb-6">
          <img src={logoUrl} alt="Mirror Pupil" className="mx-auto size-14 rounded-xl shadow-lg shadow-[color:var(--mp-crimson)]/40" />
          <h1 className="mt-4 text-2xl font-semibold tracking-tight">Mirror Pupil</h1>
          <p className="text-[10px] uppercase tracking-[0.25em] text-[color:var(--mp-text-dim)] mt-1">
            Knights of the Blood Oath
          </p>
        </div>

        <div className="rounded-2xl border border-[color:var(--mp-border)] bg-[color:var(--mp-base)]/80 backdrop-blur p-6 shadow-2xl shadow-black/40">
          <div className="flex gap-1 p-1 rounded-lg bg-white/5 mb-5 text-xs font-medium">
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-md transition-colors ${
                  mode === m
                    ? "bg-[color:var(--mp-red)] text-white"
                    : "text-[color:var(--mp-text-dim)] hover:text-white"
                }`}
              >
                {m === "signin" ? "Sign in" : "Sign up"}
              </button>
            ))}
          </div>

          <Button
            type="button"
            onClick={onGoogle}
            disabled={busy}
            className="w-full h-11 bg-white text-black hover:bg-white/90 gap-2"
          >
            <GoogleMark />
            Continue with Google
          </Button>

          <div className="flex items-center gap-3 my-5 text-[10px] uppercase tracking-widest text-[color:var(--mp-text-dim)]">
            <span className="h-px flex-1 bg-[color:var(--mp-border)]" />
            or
            <span className="h-px flex-1 bg-[color:var(--mp-border)]" />
          </div>

          <form onSubmit={onPassword} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-xs uppercase tracking-wider text-[color:var(--mp-text-dim)]">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="knight@bloodoath.io"
                required
                className="bg-[color:var(--mp-app)] border-[color:var(--mp-border)]"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs uppercase tracking-wider text-[color:var(--mp-text-dim)]">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="bg-[color:var(--mp-app)] border-[color:var(--mp-border)]"
              />
            </div>
            <Button
              type="submit"
              disabled={busy}
              className="w-full h-11 bg-gradient-to-br from-[color:var(--mp-crimson)] to-[color:var(--mp-red)] hover:opacity-95 text-white"
            >
              {mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="mt-5 text-[11px] text-center text-[color:var(--mp-text-dim)]">
            By continuing you agree to your firm's trading policy and risk profile.
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.8 2.71v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.84.86-3.05.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A8.99 8.99 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A8.99 8.99 0 0 0 0 9c0 1.45.35 2.82.96 4.05l3.01-2.33z" fill="#FBBC05"/>
      <path d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A8.99 8.99 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}
