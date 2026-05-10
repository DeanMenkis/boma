"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
  type User,
} from "firebase/auth";
import { useRouter } from "next/navigation";

import { getFirebaseAuth, getGoogleProvider } from "@/lib/firebase";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  /** Sign in with email and password. */
  signIn: (email: string, password: string) => Promise<void>;
  /** Create a new account with email, password and optional display name. */
  signUp: (email: string, password: string, name?: string) => Promise<void>;
  /** Sign in / sign up via Google popup. */
  signInWithGoogle: () => Promise<void>;
  /** Sign the current user out and redirect to /. */
  logOut: () => Promise<void>;
  /** Get a fresh Firebase ID token for API calls (auto-refreshes). */
  getIdToken: () => Promise<string | null>;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(getFirebaseAuth(), (firebaseUser) => {
      setUser(firebaseUser);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
      router.push("/app");
    },
    [router],
  );

  const signUp = useCallback(
    async (email: string, password: string, name?: string) => {
      const { user: newUser } = await createUserWithEmailAndPassword(
        getFirebaseAuth(),
        email,
        password,
      );
      if (name) {
        await updateProfile(newUser, { displayName: name });
      }
      router.push("/app");
    },
    [router],
  );

  const signInWithGoogle = useCallback(async () => {
    await signInWithPopup(getFirebaseAuth(), getGoogleProvider());
    router.push("/app");
  }, [router]);

  const logOut = useCallback(async () => {
    await signOut(getFirebaseAuth());
    router.push("/");
  }, [router]);

  const getIdToken = useCallback(async (): Promise<string | null> => {
    const current = getFirebaseAuth().currentUser;
    if (!current) return null;
    return current.getIdToken();
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, signIn, signUp, signInWithGoogle, logOut, getIdToken }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
