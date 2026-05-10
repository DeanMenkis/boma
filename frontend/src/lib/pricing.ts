/** BOMA service fee shown on marketing / pricing — keep in sync with product billing if enforced server-side. */

export const BOMA_BASE_FEE_USD = 1;
export const BOMA_PER_LINE_USD = 0.1;

export function computeBomaFeeUsd(lineCount: number) {
  const n = Math.max(0, Math.floor(lineCount));
  return BOMA_BASE_FEE_USD + BOMA_PER_LINE_USD * n;
}
