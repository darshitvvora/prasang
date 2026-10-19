from types import SimpleNamespace

import pytest

from app.notifications.templates import render

URL = "https://prasang.in"
USER = SimpleNamespace(full_name="Arjun Malhotra")


@pytest.mark.parametrize("kind, context, sms", [
    ("welcome_artist", {}, "Welcome to Prasang! Finish your profile so planners can find you: https://prasang.in/artist/onboarding"),
    ("welcome_planner", {}, "Welcome to Prasang! Find artists for your next event: https://prasang.in/search"),
    ("trial_ending", {"plan": "Pro", "date": "21 Oct 2026"}, "Your Prasang Pro trial ends on 21 Oct 2026. Keep your plan: https://prasang.in/pricing"),
    ("renewal_reminder", {"plan": "Pro", "date": "1 Nov 2026"},
     "Your Prasang Pro plan renews on 1 Nov 2026. Manage it: https://prasang.in/artist/subscription"),
    ("payment_failed", {"plan": "Pro"},
     "We couldn't charge your Prasang Pro plan. Update payment to keep it: https://prasang.in/artist/subscription"),
    ("plan_ended", {"plan": "Pro"}, "Your Prasang Pro plan has ended and you're now on Free. Upgrade: https://prasang.in/pricing"),
    ("booking_check_1", {"artist": "Arjun Malhotra", "event": "wedding"},
     "Did you book Arjun Malhotra for your wedding? Tell us: https://prasang.in/planner/inquiries"),
    ("booking_check_2_reminder", {"artist": "Arjun Malhotra", "event": "wedding"},
     "Did you book Arjun Malhotra for your wedding? Tell us: https://prasang.in/planner/inquiries"),
])
def test_templates_exact_copy(kind, context, sms):
    msg = render(kind, USER, context, URL)
    assert msg.sms == sms
    assert msg.email_subject
    assert sms.rsplit(": ", 1)[1] in msg.email_text  # the email carries the same link
