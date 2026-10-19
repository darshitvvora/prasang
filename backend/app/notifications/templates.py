"""Copy for lifecycle and booking messages. SMS = one sentence + one link (DLT-template friendly)."""
from dataclasses import dataclass
from typing import Literal

MessageKind = Literal[
    "welcome_artist", "welcome_planner", "trial_ending", "renewal_reminder", "payment_failed", "plan_ended",
    "booking_check_1", "booking_check_1_reminder", "booking_check_2", "booking_check_2_reminder",
]


@dataclass(frozen=True)
class RenderedMessage:
    sms: str
    email_subject: str
    email_text: str


def render(kind: str, user, context: dict, base_url: str) -> RenderedMessage:
    url = base_url.rstrip("/")
    c = context
    first = (user.full_name or "").split(" ")[0] or "there"
    if kind == "welcome_artist":
        link = f"{url}/artist/onboarding"
        sms = f"Welcome to Prasang! Finish your profile so planners can find you: {link}"
        return RenderedMessage(sms, "Welcome to Prasang", f"Hi {first},\n\nWelcome to Prasang! Finish your profile so planners "
                               f"can find you — add photos, videos and your social links:\n{link}\n\nTeam Prasang")
    if kind == "welcome_planner":
        link = f"{url}/search"
        sms = f"Welcome to Prasang! Find artists for your next event: {link}"
        return RenderedMessage(sms, "Welcome to Prasang", f"Hi {first},\n\nWelcome to Prasang! Find DJs, singers, magicians and "
                               f"more for your next event — it's free for planners:\n{link}\n\nTeam Prasang")
    if kind == "trial_ending":
        link = f"{url}/pricing"
        sms = f"Your Prasang {c['plan']} trial ends on {c['date']}. Keep your plan: {link}"
        return RenderedMessage(sms, f"Your {c['plan']} trial ends on {c['date']}",
                               f"Hi {first},\n\nYour Prasang {c['plan']} trial ends on {c['date']}. After that your profile "
                               f"moves to the Free plan. Keep your plan:\n{link}\n\nTeam Prasang")
    if kind == "renewal_reminder":
        link = f"{url}/artist/subscription"
        sms = f"Your Prasang {c['plan']} plan renews on {c['date']}. Manage it: {link}"
        return RenderedMessage(sms, f"Your {c['plan']} plan renews on {c['date']}",
                               f"Hi {first},\n\nYour Prasang {c['plan']} annual plan renews on {c['date']}. "
                               f"You can manage or cancel it here:\n{link}\n\nTeam Prasang")
    if kind == "payment_failed":
        link = f"{url}/artist/subscription"
        sms = f"We couldn't charge your Prasang {c['plan']} plan. Update payment to keep it: {link}"
        return RenderedMessage(sms, f"Payment failed for your {c['plan']} plan",
                               f"Hi {first},\n\nWe couldn't charge your Prasang {c['plan']} plan. Update your payment method "
                               f"with Razorpay to keep your plan:\n{link}\n\nTeam Prasang")
    if kind == "plan_ended":
        link = f"{url}/pricing"
        sms = f"Your Prasang {c['plan']} plan has ended and you're now on Free. Upgrade: {link}"
        return RenderedMessage(sms, f"Your {c['plan']} plan has ended",
                               f"Hi {first},\n\nYour Prasang {c['plan']} plan has ended and your profile is now on the Free "
                               f"plan. Upgrade any time:\n{link}\n\nTeam Prasang")
    if kind.startswith("booking_check_"):
        link = f"{url}/planner/inquiries"
        sms = f"Did you book {c['artist']} for your {c['event']}? Tell us: {link}"
        return RenderedMessage(sms, f"Did you book {c['artist']}?",
                               f"Hi {first},\n\nDid you book {c['artist']} for your {c['event']}? Let us know — once you've "
                               f"booked, you can leave a review that helps other planners:\n{link}\n\nTeam Prasang")
    raise ValueError(f"unknown message kind {kind!r}")
