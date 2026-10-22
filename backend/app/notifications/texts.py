"""SMS / WhatsApp message types: one MSG91 template per kind, with named variables.

Each kind goes out on WhatsApp (a Meta-approved template; no DLT needed) or SMS (only with a DLT-registered template).
A kind uses SMS if MSG91_SMS_TEMPLATE_<KIND> is set, else WhatsApp if MSG91_WHATSAPP_TEMPLATE_<KIND> is set, else it is
skipped (email still goes out). WhatsApp templates use the same wording with {{1}}, {{2}}… (see `whatsapp_body`).
`python -m app.cli msg91-templates` prints everything to register and which env vars are still empty.
"""
import re
from dataclasses import dataclass, field

# kind -> template text with ##variable## placeholders (MSG91 Flow syntax). Keep each to one sentence + one link.
SMS_TEMPLATES: dict[str, str] = {
    "otp": "##otp## is your Prasang login code. It expires in ##minutes## minutes.",
    "lead": "New lead on Prasang! ##planner## wants to book you for a ##event## on ##date##, budget ##budget##. "
            "Call them: +91 ##phone## ##link##",
    "lead_locked": "New lead on Prasang for a ##event## on ##date##, budget ##budget##. You've reached this month's lead limit - "
                   "upgrade to see their details: ##link##",
    "welcome_artist": "Welcome to Prasang! Finish your profile so planners can find you: ##link##",
    "welcome_planner": "Welcome to Prasang! Find artists for your next event: ##link##",
    "trial_ending": "Your Prasang ##plan## trial ends on ##date##. Keep your plan: ##link##",
    "payment_link": "Pay ##amount## for your Prasang ##plan## plan (##cycle##) with PhonePe: ##link##",
    "renewal_due": "Your Prasang ##plan## plan ends on ##date##. Renew for ##amount## with PhonePe: ##link##",
    "payment_received": "Payment of ##amount## received. Your Prasang ##plan## plan is active until ##date##: ##link##",
    "plan_ended": "Your Prasang ##plan## plan has ended and you're now on Free. Upgrade: ##link##",
    "media_removal": "Your Prasang plan changed: ##count## photos/videos are hidden and will be deleted on ##date##. "
                     "Upgrade to keep them: ##link##",
    "booking_check": "Did you book ##artist## for your ##event##? Tell us: ##link##",
}

# Every kind can go out on WhatsApp. The OTP must be a Meta "Authentication" template, whose wording Meta fixes:
# "<code> is your verification code." with a copy-code button — so it carries the code only.
WHATSAPP_KINDS = tuple(SMS_TEMPLATES)
WHATSAPP_AUTH_KINDS = ("otp",)

VAR_MAX = 30  # DLT limit per {#var#}; links are exempt (MSG91 shortens them)
_VAR = re.compile(r"##(\w+)##")


def variables_of(kind: str) -> list[str]:
    """Variable names in the order they appear (= {{1}}, {{2}}… on WhatsApp)."""
    return _VAR.findall(SMS_TEMPLATES[kind])


def whatsapp_variables_of(kind: str) -> list[str]:
    return ["otp"] if kind in WHATSAPP_AUTH_KINDS else variables_of(kind)


def _fill(kind: str, variables: dict[str, str], placeholder) -> str:
    return _VAR.sub(lambda m: placeholder(m.group(1)), SMS_TEMPLATES[kind])


@dataclass(frozen=True)
class TextMessage:
    """One SMS/WhatsApp message: a template kind plus its variable values."""

    kind: str
    variables: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        missing = set(variables_of(self.kind)) - set(self.variables)
        if missing:
            raise ValueError(f"{self.kind}: missing variables {sorted(missing)}")

    @property
    def text(self) -> str:
        return _fill(self.kind, self.variables, lambda name: str(self.variables[name]))

    def values(self, channel: str = "sms") -> dict[str, str]:
        """Values as sent to MSG91, in template order: single line; on SMS, non-link values are cut to the DLT limit."""
        names = whatsapp_variables_of(self.kind) if channel == "whatsapp" else variables_of(self.kind)
        out = {}
        for name in names:
            value = " ".join(str(self.variables[name]).split())  # WhatsApp rejects newlines/tabs in variables
            out[name] = value if name == "link" or channel == "whatsapp" else value[:VAR_MAX]
        return out


WHATSAPP_SIGNATURE = " - Team Prasang"  # Meta rejects template bodies that start or end with a variable


def whatsapp_body(kind: str) -> str:
    """The template body to create in MSG91 → WhatsApp → Templates."""
    if kind in WHATSAPP_AUTH_KINDS:
        return ("{{1}} is your verification code. (Meta's fixed Authentication wording; tick the 10-minute expiry note and "
                "add a Copy code button)")
    names = variables_of(kind)
    return _fill(kind, {}, lambda name: "{{" + str(names.index(name) + 1) + "}}") + WHATSAPP_SIGNATURE


def template_report(settings) -> str:
    """What to register where, and which env vars are still empty (`python -m app.cli msg91-templates`)."""
    sms, wa = settings.msg91_templates("sms"), settings.msg91_templates("whatsapp")
    lines = [f"WhatsApp — create in MSG91 → WhatsApp → Templates (language {settings.msg91_whatsapp_language}; category Utility, "
             "OTP = Authentication) and put the template name in the env var. No DLT needed.", ""]
    for kind in WHATSAPP_KINDS:
        names = whatsapp_variables_of(kind)
        lines += [f"[{'set' if kind in wa else '   '}] MSG91_WHATSAPP_TEMPLATE_{kind.upper()}",
                  f"    Body:  {whatsapp_body(kind)}",
                  f"    ({', '.join(f'{{{{{i}}}}} = {name}' for i, name in enumerate(names, start=1))})", ""]
    lines += ["SMS (optional, only with DLT) — register the DLT: line on a DLT portal, add the MSG91: line in MSG91 → SMS →",
              "Templates and put its template id in the env var. A kind with an SMS template uses SMS instead of WhatsApp.", ""]
    for kind, text in SMS_TEMPLATES.items():
        lines += [f"[{'set' if kind in sms else '   '}] MSG91_SMS_TEMPLATE_{kind.upper()}",
                  f"    DLT:   {_VAR.sub('{#var#}', text)}",
                  f"    MSG91: {text}", ""]
    channel = {k: "SMS" if k in sms else "WhatsApp" if k in wa and settings.msg91_whatsapp_number else "not sent" for k in SMS_TEMPLATES}
    lines.append("Channel now: " + ", ".join(f"{k}={v}" for k, v in channel.items()))
    lines.append(f"MSG91_AUTH_KEY {'set' if settings.msg91_auth_key else 'NOT set (everything is only logged)'} · "
                 f"MSG91_WHATSAPP_NUMBER {'set' if settings.msg91_whatsapp_number else 'NOT set'}")
    return "\n".join(lines)
