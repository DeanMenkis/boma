/** Demo BOM used on the landing page scroll animation and stats — keep totals in sync here. */

export type MarketingBomRow = {
  part: string;
  desc: string;
  qty: number;
  unit: number;
};

export const MARKETING_BOM: MarketingBomRow[] = [
  { part: "ATMEGA328P-PU", desc: "MCU 8-bit AVR 32KB", qty: 5, unit: 2.21 },
  { part: "LM7805CT", desc: "LDO 5V 1A TO-220", qty: 10, unit: 0.58 },
  { part: "RC0805FR-074K7L", desc: "Resistor 4.7k 1% 0805", qty: 100, unit: 0.42 },
  { part: "CL21B104KBCNNNC", desc: "Cap 100nF 50V X7R 0805", qty: 50, unit: 0.04 },
  { part: "SK6812-3535", desc: "Addressable RGB LED", qty: 25, unit: 0.36 },
];

export const MARKETING_BOM_LINE_COUNT = MARKETING_BOM.length;

export const MARKETING_BOM_UNIT_COUNT = MARKETING_BOM.reduce((sum, row) => sum + row.qty, 0);

export const MARKETING_BOM_SUBTOTAL = MARKETING_BOM.reduce(
  (sum, row) => sum + row.qty * row.unit,
  0,
);

export function formatMarketingCurrency(value: number) {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}
