// Razorpay Checkout for subscriptions. Loads checkout.js on demand and resolves
// with the ids the backend needs to verify the payment signature.
// Mock mode: key ids starting with `rzp_test_mock` resolve immediately (Mockoon).
import type { CreateSubscriptionResponse, VerifyPaymentRequest } from '../api/types';
import { ApiError } from '../api/client';

type Checkout = CreateSubscriptionResponse['checkout'];

interface RazorpayResponse { razorpay_payment_id: string; razorpay_subscription_id: string; razorpay_signature: string }
interface RazorpayInstance { open(): void; on(event: 'payment.failed', cb: () => void): void }
type RazorpayCtor = new (options: Record<string, unknown>) => RazorpayInstance;

const SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';
let scriptPromise: Promise<RazorpayCtor> | null = null;

function loadScript(): Promise<RazorpayCtor> {
  const existing = (window as unknown as { Razorpay?: RazorpayCtor }).Razorpay;
  if (existing) return Promise.resolve(existing);
  scriptPromise ??= new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = SCRIPT_URL;
    s.async = true;
    s.onload = () => resolve((window as unknown as { Razorpay: RazorpayCtor }).Razorpay);
    s.onerror = () => {
      scriptPromise = null;
      reject(new ApiError(0, 'checkout_unavailable', 'Could not load the payment window. Check your connection and try again.'));
    };
    document.body.appendChild(s);
  });
  return scriptPromise;
}

export async function openCheckout(checkout: Checkout): Promise<VerifyPaymentRequest> {
  if (checkout.keyId.startsWith('rzp_test_mock')) {
    return {
      razorpayPaymentId: `pay_mock${Date.now()}`,
      razorpaySubscriptionId: checkout.razorpaySubscriptionId,
      razorpaySignature: 'mock-signature',
    };
  }
  const Razorpay = await loadScript();
  return new Promise((resolve, reject) => {
    const rzp = new Razorpay({
      key: checkout.keyId,
      subscription_id: checkout.razorpaySubscriptionId,
      name: checkout.name,
      description: checkout.description,
      prefill: checkout.prefill,
      theme: { color: '#d4f53f' },
      handler: (r: RazorpayResponse) => resolve({
        razorpayPaymentId: r.razorpay_payment_id,
        razorpaySubscriptionId: r.razorpay_subscription_id,
        razorpaySignature: r.razorpay_signature,
      }),
      modal: { ondismiss: () => reject(new ApiError(0, 'checkout_dismissed', 'Payment was cancelled.')) },
    });
    rzp.on('payment.failed', () => reject(new ApiError(0, 'payment_failed', 'Payment failed. No money was taken — please try again.')));
    rzp.open();
  });
}
