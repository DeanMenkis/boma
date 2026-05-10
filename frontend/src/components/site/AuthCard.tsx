"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Boxes } from "lucide-react";
import { useState, type FormEvent } from "react";

type Props = {
  mode: "login" | "signup";
};

export function AuthCard({ mode }: Props) {
  const isSignup = mode === "signup";
  const [loading, setLoading] = useState(false);

  const runPlaceholderAuth = async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    alert(`${isSignup ? "Sign up" : "Log in"} flow is a placeholder — wire Firebase to enable.`);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await runPlaceholderAuth();
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-12 relative">
      <div className="absolute inset-0 bg-grid opacity-50 pointer-events-none" />
      <div className="absolute inset-0 bg-hero pointer-events-none" />

      <Link href="/" className="relative flex items-center gap-2 mb-8">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-glow">
          <Boxes className="h-5 w-5" />
        </div>
        <span className="font-mono text-sm">BOMA</span>
      </Link>

      <div className="relative w-full max-w-sm rounded-2xl border border-border glass p-8 shadow-card">
        <h1 className="font-display text-3xl text-gradient">
          {isSignup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {isSignup ? "Start sourcing in under a minute." : "Pick up where you left off."}
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-3">
          {isSignup && <Field label="Name" type="text" placeholder="Ada Lovelace" />}
          <Field label="Email" type="email" placeholder="you@company.com" required />
          <Field label="Password" type="password" placeholder="••••••••" required />

          <Button type="submit" variant="hero" size="lg" className="w-full mt-2" disabled={loading}>
            {loading ? "…" : isSignup ? "Create account" : "Log in"}
          </Button>
        </form>

        <div className="my-5 flex items-center gap-3 text-xs font-mono text-muted-foreground">
          <span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" />
        </div>

        <Button
          variant="glass"
          size="lg"
          className="w-full"
          type="button"
          disabled={loading}
          onClick={() => void runPlaceholderAuth()}
        >
          <GoogleIcon /> Continue with Google
        </Button>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          {isSignup ? (
            <>
              Already have an account?{" "}
              <Link href="/login" className="text-foreground hover:text-primary">
                Log in
              </Link>
            </>
          ) : (
            <>
              New to BOMA?{" "}
              <Link href="/signup" className="text-foreground hover:text-primary">
                Create one
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  ...rest
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-xs font-mono text-muted-foreground">{label}</span>
      <input
        {...rest}
        className="mt-1 w-full rounded-lg bg-surface-2 border border-border px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring transition"
      />
    </label>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path
        fill="#EA4335"
        d="M12 10.2v3.9h5.5c-.24 1.4-1.7 4.1-5.5 4.1-3.3 0-6-2.7-6-6.2s2.7-6.2 6-6.2c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.7 3.3 14.6 2.4 12 2.4 6.7 2.4 2.4 6.7 2.4 12s4.3 9.6 9.6 9.6c5.5 0 9.2-3.9 9.2-9.4 0-.6-.07-1.1-.16-1.6H12z"
      />
    </svg>
  );
}
