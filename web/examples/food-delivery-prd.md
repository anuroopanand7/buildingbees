# QuickBite: Order and Pay (PRD v0.3)

## Goal
Let a hungry customer go from a restaurant menu to a paid, confirmed order in under 60 seconds.

## Users
- Customer: orders food on the mobile web app.
- Restaurant partner: accepts or rejects incoming orders on a tablet.

## Flow 1: Customer checkout
1. **Cart screen.** Shows items, quantities, restaurant name and subtotal. Customer can change quantity or remove an item. "Apply coupon" field. "Proceed to checkout" button.
2. **Address screen.** Customer picks a saved address or adds a new one. We check the restaurant delivers to that pincode. "Continue" button.
3. **Payment screen.** UPI, card, or cash on delivery. Shows final total with delivery fee and taxes. "Pay now" button calls the payment gateway (Razorpay).
4. **Order confirmed screen.** Shows order id, estimated delivery time, and a "Track order" button.

## Flow 2: Restaurant accepts order
1. **Incoming order screen.** New orders appear with items and a 90 second countdown. "Accept" and "Reject" buttons.
2. When accepted, the customer sees "Preparing your food".

## APIs
- `POST /cart/validate`: re-checks prices and item availability.
- `POST /coupons/apply`: validates a coupon code.
- `GET /serviceability?pincode=`: checks delivery coverage (vendor: Shadowfax).
- `POST /payments/create`: creates a Razorpay order.
- `POST /orders`: places the order.
- `POST /orders/{id}/accept` and `POST /orders/{id}/reject`.

## Notes
- Coupons: one per order.
- Cash on delivery only for orders under Rs 1500.
