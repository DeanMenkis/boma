"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { FileSpreadsheet, Loader2, Trash2, User } from "lucide-react";

import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useSavedBoms } from "@/hooks/useSavedBoms";

export function ProfilePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { savedBoms, removeSavedBom } = useSavedBoms(user?.uid ?? null);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (!user && !loading) {
    return null;
  }

  if (loading || !user) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <section className="mx-auto w-full max-w-3xl px-6 pt-12 pb-6">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-border bg-card shadow-card">
            <User className="h-7 w-7 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-xs text-primary uppercase tracking-widest">Profile</p>
            <h1 className="mt-1 font-display text-4xl text-gradient">
              {user.displayName ?? "Your workspace"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground font-mono truncate">{user.email}</p>
            <p className="mt-3 text-sm text-muted-foreground max-w-xl">
              Saved BOMs are stored in this browser only. Sign in on another device to start fresh,
              or export carts from the agent when we add cloud sync.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
          Saved BOMs
        </h2>

        {savedBoms.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-border bg-card/40 px-6 py-12 text-center">
            <p className="text-sm text-muted-foreground">
              Nothing saved yet. Run the agent on{" "}
              <Link
                href="/app"
                className="text-foreground hover:text-primary underline-offset-4 hover:underline"
              >
                the upload page
              </Link>{" "}
              and click <span className="font-mono text-foreground">Save to profile</span>.
            </p>
          </div>
        ) : (
          <ul className="mt-4 space-y-3">
            {savedBoms.map((bom) => (
              <li
                key={bom.id}
                className="rounded-2xl border border-border bg-card p-4 shadow-card flex flex-wrap items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="font-medium truncate">{bom.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground font-mono flex flex-wrap gap-x-3 gap-y-1">
                    <span>{bom.lineCount} lines</span>
                    <span>${bom.subtotal.toFixed(2)}</span>
                    <span>{formatSavedAt(bom.savedAt)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button variant="hero" size="sm" asChild>
                    <Link href={`/app?load=${encodeURIComponent(bom.id)}`}>Open in agent</Link>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive"
                    aria-label={`Delete ${bom.title}`}
                    onClick={() => removeSavedBom(bom.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Footer />
    </div>
  );
}

function formatSavedAt(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
