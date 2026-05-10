/** One line in a priced BOM cart (agent table). */
export type BomCartRow = {
  part: string;
  desc: string;
  qty: number;
  distributor: "DigiKey" | "Mouser";
  unit: number;
  stock: number;
  eta: string;
  url: string;
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
