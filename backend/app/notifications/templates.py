"""Copy for lifecycle and booking messages. SMS wording lives in texts.py (one DLT template per kind)."""
from dataclasses import dataclass
from typing import Literal

from app.notifications.texts import TextMessage

MessageKind = Literal[
    "welcome_artist", "welcome_planner", "trial_ending", "payment_link", "renewal_due", "payment_received", "plan_ended",
    "booking_check_1", "booking_check_1_reminder", "booking_check_2", "booking_check_2_reminder", "media_removal",
]


@dataclass(frozen=True)
class RenderedMessage:
    sms: TextMessage  # template kind + variables (texts.py); `.text` is the SMS as delivered
    email_subject: str
    email_text: str


def render(kind: str, user, context: dict, base_url: str) -> RenderedMessage:
    url = base_url.rstrip("/")
    c = context
    first = (user.full_name or "").split(" ")[0] or "there"
    if kind == "welcome_artist":
        link = f"{url}/artist/onboarding"
        sms = TextMessage("welcome_artist", {"link": link})
        return RenderedMessage(sms, "Welcome to Prasang", f"Hi {first},\n\nWelcome to Prasang! Finish your profile so planners "
                               f"can find you — add photos, videos and your social links:\n{link}\n\nTeam Prasang")
    if kind == "welcome_planner":
        link = f"{url}/search"
        sms = TextMessage("welcome_planner", {"link": link})
        return RenderedMessage(sms, "Welcome to Prasang", f"Hi {first},\n\nWelcome to Prasang! Find DJs, singers, magicians and "
                               f"more for your next event — it's free for planners:\n{link}\n\nTeam Prasang")
    if kind == "trial_ending":
        link = f"{url}/pricing"
        sms = TextMessage("trial_ending", {"plan": c["plan"], "date": c["date"], "link": link})
        return RenderedMessage(sms, f"Your {c['plan']} trial ends on {c['date']}",
                               f"Hi {first},\n\nYour Prasang {c['plan']} trial ends on {c['date']}. After that your profile "
                               f"moves to the Free plan. Keep your plan:\n{link}\n\nTeam Prasang")
    if kind == "payment_link":
        sms = TextMessage("payment_link", {"amount": c["amount"], "plan": c["plan"], "cycle": c["cycle"], "link": c["url"]})
        return RenderedMessage(sms, f"Your Prasang {c['plan']} payment link",
                               f"Hi {first},\n\nHere is your PhonePe link to pay {c['amount']} for the Prasang {c['plan']} plan "
                               f"({c['cycle']}). Pay with UPI, card or net banking — your plan starts as soon as the payment "
                               f"goes through:\n{c['url']}\n\nThe link works until {c['pay_by']}.\n\nTeam Prasang")
    if kind == "renewal_due":
        sms = TextMessage("renewal_due", {"plan": c["plan"], "date": c["date"], "amount": c["amount"], "link": c["url"]})
        return RenderedMessage(sms, f"Renew your {c['plan']} plan — it ends on {c['date']}",
                               f"Hi {first},\n\nYour Prasang {c['plan']} plan ends on {c['date']}. Renew it for {c['amount']} "
                               f"({c['cycle']}) with this PhonePe link — the new period starts when the current one ends, so "
                               f"paying early loses nothing:\n{c['url']}\n\nThe link works until {c['pay_by']}. If you don't "
                               f"renew, your profile moves to the Free plan after that.\n\nTeam Prasang")
    if kind == "payment_received":
        link = f"{url}/artist/subscription"
        sms = TextMessage("payment_received", {"amount": c["amount"], "plan": c["plan"], "date": c["date"], "link": link})
        return RenderedMessage(sms, f"Payment received — {c['plan']} plan active until {c['date']}",
                               f"Hi {first},\n\nThanks! We received {c['amount']} for your Prasang {c['plan']} plan. It is "
                               f"active until {c['date']}; we'll send a renewal link a few days before then. Your payments "
                               f"are listed here:\n{link}\n\nKeep this email as your receipt.\n\nTeam Prasang")
    if kind == "plan_ended":
        link = f"{url}/pricing"
        sms = TextMessage("plan_ended", {"plan": c["plan"], "link": link})
        return RenderedMessage(sms, f"Your {c['plan']} plan has ended",
                               f"Hi {first},\n\nYour Prasang {c['plan']} plan has ended and your profile is now on the Free "
                               f"plan. Upgrade any time:\n{link}\n\nTeam Prasang")
    if kind == "media_removal":
        link = f"{url}/pricing"
        sms = TextMessage("media_removal", {"count": str(c["count"]), "date": c["date"], "link": link})
        return RenderedMessage(sms, f"{c['count']} photos/videos will be deleted on {c['date']}",
                               f"Hi {first},\n\nYour Prasang plan now allows fewer photos, videos or embeds, so {c['count']} items "
                               f"are hidden from your profile and will be deleted on {c['date']}. Upgrade before then to keep "
                               f"them, or reorder your media to choose what stays:\n{link}\n\nTeam Prasang")
    if kind.startswith("booking_check_"):
        link = f"{url}/planner/inquiries"
        sms = TextMessage("booking_check", {"artist": c["artist"], "event": c["event"], "link": link})
        return RenderedMessage(sms, f"Did you book {c['artist']}?",
                               f"Hi {first},\n\nDid you book {c['artist']} for your {c['event']}? Let us know — once you've "
                               f"booked, you can leave a review that helps other planners:\n{link}\n\nTeam Prasang")
    raise ValueError(f"unknown message kind {kind!r}")
