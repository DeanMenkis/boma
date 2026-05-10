/** Demo coupon: skips AllScale wallet checkout and completes export as CSV only. */
export const TEST_CHECKOUT_COUPON = "test123";

export function isTestCheckoutCoupon(code: string): boolean {
  return code.trim().toLowerCase() === TEST_CHECKOUT_COUPON;
}
