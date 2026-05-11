/** One line in a priced BOM cart (agent table). */
export type BomCartRow = {
  part: string;
  desc: string;
  qty: number;
  /** Source supplier. Currently always "DigiKey" from the backend; kept open
   * so we can add Mouser/Arrow without a breaking change. */
  distributor: string;
  unit: number;
  stock: number;
  eta: string;
  url: string;
  /** DigiKey part number — only present for rows the agent matched against
   * the live (or mock) DigiKey catalog. Needed to add the line to a
   * DigiKey MyList. */
  digikeyPartNumber?: string;
  /** Free-form confidence flag from the specialist agent. */
  matchConfidence?: "high" | "medium" | "low";
};

export type SavedBom = {
  id: string;
  title: string;
  sourceFileName: string | null;
  savedAt: string;
  lineCount: number;
  subtotal: number;
  rows: BomCartRow[];
};
