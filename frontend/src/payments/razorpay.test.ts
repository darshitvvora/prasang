import { expect, it } from 'vitest';
import { openCheckout } from './razorpay';

it('mock checkout resolves immediately with the subscription id', async () => {
  const res = await openCheckout({ keyId: 'rzp_test_mock', razorpaySubscriptionId: 'sub_mock123', name: 'Prasang', description: 'Pro', prefill: { name: 'A', email: null, contact: null } });
  expect(res.razorpaySubscriptionId).toBe('sub_mock123');
  expect(res.razorpayPaymentId).toMatch(/^pay_mock/);
  expect(res.razorpaySignature).toBeTruthy();
});
