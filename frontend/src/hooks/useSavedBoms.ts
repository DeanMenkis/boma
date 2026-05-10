"use client";

import { useCallback, useEffect, useState } from "react";

import type { SavedBom } from "@/lib/bom-types";
import {
  listSavedBoms as readSavedBomList,
  removeSavedBom as deleteStoredBom,
  upsertSavedBom as writeStoredBom,
} from "@/lib/saved-boms-storage";

export function useSavedBoms(uid: string | null) {
  const [savedBoms, setSavedBoms] = useState<SavedBom[]>([]);

  useEffect(() => {
    if (!uid) {
      setSavedBoms([]);
      return;
    }
    setSavedBoms(readSavedBomList(uid));
  }, [uid]);

  const saveSavedBom = useCallback(
    (bom: SavedBom) => {
      if (!uid) return;
      writeStoredBom(uid, bom);
      setSavedBoms(readSavedBomList(uid));
    },
    [uid],
  );

  const removeSavedBom = useCallback(
    (id: string) => {
      if (!uid) return;
      deleteStoredBom(uid, id);
      setSavedBoms(readSavedBomList(uid));
    },
    [uid],
  );

  return { savedBoms, saveSavedBom, removeSavedBom };
}
