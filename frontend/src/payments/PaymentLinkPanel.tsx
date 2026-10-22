import { useEffect, useRef } from 'react';
import { ExternalLink } from 'lucide-react';
import { useVerifyPayment } from '../api/queries';
import type { PaymentLinkInfo, VerifyPaymentResponse } from '../api/types';
import { linkDeadline } from './paymentLink';
import './PaymentLinkPanel.css';

const POLL_MS = 5000;
const POLL_FOR_MS = 15 * 60 * 1000;

interface Props {
  subscriptionId: string;
  payment: PaymentLinkInfo;
  title: string;
  onPaid: (result: VerifyPaymentResponse) => void;
}

/** "Pay with PhonePe" + "I've paid". Also checks in the background so the page updates once PhonePe confirms. */
export default function PaymentLinkPanel({ subscriptionId, payment, title, onPaid }: Props) {
  const verify = useVerifyPayment();
  const onPaidRef = useRef(onPaid);
  const { mutateAsync } = verify;
  useEffect(() => { onPaidRef.current = onPaid; }, [onPaid]);

  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(async () => {
      if (document.hidden) return;
      if (Date.now() - started > POLL_FOR_MS) {
        window.clearInterval(timer);
        return;
      }
      try {
        const result = await mutateAsync({ subscriptionId });
        if (result.status === 'active') {
          window.clearInterval(timer);
          onPaidRef.current(result);
        }
      } catch {
        // keep polling; the artist can also press "I've paid"
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [subscriptionId, mutateAsync]);

  async function check() {
    const result = await verify.mutateAsync({ subscriptionId });
    if (result.status === 'active') onPaid(result);
  }

  const waiting = verify.data?.status === 'pending_activation' && !verify.isPending;
  return (
    <div className="payment-link-panel" role="region" aria-label="Payment">
      <p className="payment-link-title">{title}</p>
      <a className="payment-link-pay" href={payment.url} target="_blank" rel="noreferrer">
        Pay ₹{payment.amount.toLocaleString('en-IN')} with PhonePe <ExternalLink size={16} />
      </a>
      <p className="payment-link-note">
        UPI, cards or net banking. We've also emailed and texted you this link — it works until {linkDeadline(payment.expiresAt)}.
      </p>
      <button type="button" className="payment-link-check" disabled={verify.isPending} onClick={() => check().catch(() => undefined)}>
        {verify.isPending ? 'Checking…' : "I've paid"}
      </button>
      {waiting && <p className="payment-link-note">We haven't heard from PhonePe yet. It usually takes a few seconds after you pay.</p>}
      {verify.isError && <p className="payment-link-error">Couldn't check right now. Please try again.</p>}
    </div>
  );
}
