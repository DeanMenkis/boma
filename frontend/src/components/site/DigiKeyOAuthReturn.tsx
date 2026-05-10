"use client";

import { Suspense, useEffect, useRef } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/**
 * Handles the redirect back from FastAPI after DigiKey OAuth:
 *   GET {BOMA_FRONTEND_URL}?digikey=ok
 *   GET {BOMA_FRONTEND_URL}?digikey=error:access_denied
 *
 * Mount once near the root layout (inside <Suspense> is optional — this file
 * wraps its own Suspense). After showing feedback it strips `digikey` from
 * the URL without a full reload.
 */
function DigiKeyOAuthReturnInner() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const handled = useRef(false);

  useEffect(() => {
    const digikey = searchParams.get("digikey");
    if (digikey == null || handled.current) return;
    handled.current = true;

    const messageOk =
      "DigiKey connected. You can enrich your BOM and push parts to your list.";
    const messageErr = (detail: string) =>
      `DigiKey login failed${detail ? `: ${detail}` : ""}.`;

    if (digikey === "ok") {
      notifyDigiKey(messageOk, "success");
    } else if (digikey.startsWith("error:")) {
      const detail = digikey.slice("error:".length).trim();
      notifyDigiKey(messageErr(detail), "error");
    }

    const params = new URLSearchParams(searchParams.toString());
    params.delete("digikey");
    const q = params.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  }, [searchParams, pathname, router]);

  return null;
}

function notifyDigiKey(message: string, kind: "success" | "error") {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { toast } = require("sonner") as typeof import("sonner");
    if (kind === "success") toast.success(message);
    else toast.error(message);
  } catch {
    // Sonner not installed or Toaster missing — still inform the user.
    // eslint-disable-next-line no-alert
    window.alert(message);
  }
}

export function DigiKeyOAuthReturn() {
  return (
    <Suspense fallback={null}>
      <DigiKeyOAuthReturnInner />
    </Suspense>
  );
}
