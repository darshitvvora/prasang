from types import SimpleNamespace

import pytest

from app.notifications.templates import render

URL = "https://prasang.in"
USER = SimpleNamespace(full_name="Arjun Malhotra")


@pytest.mark.parametrize("kind, context, sms", [
    ("welcome_artist", {}, "Welcome to Prasang! Finish your profile so planners can find you: https://prasang.in/artist/onboarding"),
    ("welcome_planner", {}, "Welcome to Prasang! Find artists for your next event: https://prasang.in/search"),
    ("trial_ending", {"plan": "Pro", "date": "21 Oct 2026"}, "Your Prasang Pro trial ends on 21 Oct 2026. Keep your plan: https://prasang.in/pricing"),
    ("payment_link", {"plan": "Pro", "cycle": "monthly", "amount": "₹599", "url": "https://phon.pe/x", "pay_by": "23 Oct 2026"},
     "Pay ₹599 for your Prasang Pro plan (monthly) with PhonePe: https://phon.pe/x"),
    ("renewal_due", {"plan": "Pro", "cycle": "monthly", "amount": "₹599", "url": "https://phon.pe/y", "pay_by": "4 Nov 2026",
                     "date": "1 Nov 2026"},
     "Your Prasang Pro plan ends on 1 Nov 2026. Renew for ₹599 with PhonePe: https://phon.pe/y"),
    ("payment_received", {"plan": "Pro", "amount": "₹599", "date": "21 Nov 2026"},
     "Payment of ₹599 received. Your Prasang Pro plan is active until 21 Nov 2026: https://prasang.in/artist/subscription"),
    ("plan_ended", {"plan": "Pro"}, "Your Prasang Pro plan has ended and you're now on Free. Upgrade: https://prasang.in/pricing"),
    ("media_removal", {"count": 3, "date": "27 Oct 2026"},
     "Your Prasang plan changed: 3 photos/videos are hidden and will be deleted on 27 Oct 2026. Upgrade to keep them: https://prasang.in/pricing"),
    ("booking_check_1", {"artist": "Arjun Malhotra", "event": "wedding"},
     "Did you book Arjun Malhotra for your wedding? Tell us: https://prasang.in/planner/inquiries"),
    ("booking_check_2_reminder", {"artist": "Arjun Malhotra", "event": "wedding"},
     "Did you book Arjun Malhotra for your wedding? Tell us: https://prasang.in/planner/inquiries"),
])
def test_templates_exact_copy(kind, context, sms):
    msg = render(kind, USER, context, URL)
    assert msg.sms.text == sms  # the DLT template filled in (texts.py) reads exactly like this
    assert msg.email_subject
    assert sms.rsplit(": ", 1)[1] in msg.email_text  # the email carries the same link
