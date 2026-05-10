"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Boxes, Loader2, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";

export function Header() {
  const pathname = usePathname();
  const { user, loading, logOut, signingOut } = useAuth();

  return (
    <header className="sticky top-0 z-50 glass">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-glow">
            <Boxes className="h-4 w-4" />
          </div>
          <span className="font-mono text-sm tracking-tight">
            BOMA<span className="text-muted-foreground">/agent</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-sm">
          <Link
            href="/"
            className={cn(
              "px-3 py-1.5 transition-colors",
              pathname === "/" ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            Home
          </Link>
          <Link
            href="/pricing"
            className={cn(
              "px-3 py-1.5 transition-colors",
              pathname === "/pricing"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Pricing
          </Link>
          <Link
            href="/app"
            className={cn(
              "px-3 py-1.5 transition-colors",
              pathname === "/app" || pathname.startsWith("/app/")
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Agent
          </Link>
          {user && (
            <Link
              href="/profile"
              className={cn(
                "px-3 py-1.5 transition-colors",
                pathname === "/profile"
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              Profile
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {user && !loading ? (
            <>
              <span className="hidden sm:block text-sm text-muted-foreground max-w-[160px] truncate">
                {user.displayName ?? user.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void logOut()}
                disabled={signingOut}
                className="gap-1.5 min-w-[7.5rem]"
              >
                {signingOut ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                    Signing out…
                  </>
                ) : (
                  <>
                    <LogOut className="h-3.5 w-3.5" aria-hidden />
                    Sign out
                  </>
                )}
              </Button>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Log in
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="hero" size="sm">
                  Get started
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
