"""`python -m app.cli admin <command> …` — run on the server (SSM) or locally via `docker compose exec api`."""
import argparse
import asyncio
import getpass
import sys

from app.errors import AppError

REASON = {"required": True, "help": "why (stored in the audit log)"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli admin", description="Prasang admin actions (each one is audit-logged)")
    parser.add_argument("--actor", default=None, help="who is acting (default: your OS user)")
    sub = parser.add_subparsers(dest="command", required=True)

    def cmd(name: str, help_: str, *positional: str, reason: bool = False) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        for arg in positional:
            p.add_argument(arg)
        if reason:
            p.add_argument("--reason", **REASON)
        return p

    cmd("make-admin", "give a user the admin role", "user")
    cmd("verify", "show the verified badge", "slug")
    cmd("unverify", "remove the verified badge", "slug")
    cmd("feature", "feature on the home page regardless of plan", "slug")
    cmd("unfeature", "stop featuring (plan featuring still applies)", "slug")
    cmd("suspend", "hide an artist from search and their public link (billing keeps running)", "slug", reason=True)
    cmd("restore", "undo a suspension", "slug")
    grant = cmd("grant-plan", "give a paid plan for N days", "slug", "tier", reason=True)
    grant.add_argument("--days", type=int, required=True)
    cmd("hide-review", "hide a review from the profile and rating", "review_id", reason=True)
    cmd("restore-review", "show a hidden review again", "review_id")
    cmd("block-user", "block a user (artists are also suspended and billing cancelled)", "user", reason=True)
    cmd("unblock-user", "undo a block", "user")
    cmd("sync-subscription", "re-read the artist's subscription from Razorpay and apply it", "slug")
    cmd("clear-google-place", "remove a wrong or abusive Google listing from a profile", "slug")
    cmd("reports", "list reported reviews and the latest contact messages")
    return parser


async def _run(args: argparse.Namespace) -> str:
    from app.admin import actions
    from app.db import get_sessionmaker

    actor = args.actor or getpass.getuser() or "cli"
    calls = {
        "make-admin": lambda s: actions.make_admin(s, args.user, actor=actor),
        "verify": lambda s: actions.set_verified(s, args.slug, True, actor=actor),
        "unverify": lambda s: actions.set_verified(s, args.slug, False, actor=actor),
        "feature": lambda s: actions.set_featured(s, args.slug, True, actor=actor),
        "unfeature": lambda s: actions.set_featured(s, args.slug, False, actor=actor),
        "suspend": lambda s: actions.suspend(s, args.slug, actor=actor, reason=args.reason),
        "restore": lambda s: actions.restore(s, args.slug, actor=actor),
        "grant-plan": lambda s: actions.grant_plan(s, args.slug, args.tier, args.days, actor=actor, reason=args.reason),
        "hide-review": lambda s: actions.hide_review(s, args.review_id, actor=actor, reason=args.reason),
        "restore-review": lambda s: actions.restore_review(s, args.review_id, actor=actor),
        "block-user": lambda s: actions.block_user(s, args.user, actor=actor, reason=args.reason),
        "unblock-user": lambda s: actions.unblock_user(s, args.user, actor=actor),
        "sync-subscription": lambda s: actions.sync_subscription(s, args.slug, actor=actor),
        "clear-google-place": lambda s: actions.clear_google_place(s, args.slug, actor=actor),
    }
    if args.command == "reports":
        async with get_sessionmaker()() as session:
            data = await actions.open_reports(session)
        reviews = [f"  {r['review_id']}  {r['rating']}★  reason: {r['reason']}\n      {r['text']}" for r in data["reviews"]]
        contact = [f"  {m['at'][:16]}  [{m['topic']}] {m['from']}: {m['message']}" for m in data["contact"]]
        lines = ["Reported reviews:", *(reviews or ["  none"]), "Latest contact messages:", *(contact or ["  none"])]
        return "\n".join(lines)
    async with get_sessionmaker()() as session:
        await calls[args.command](session)
    return f"ok: {args.command} {' '.join(str(v) for k, v in vars(args).items() if k not in ('command', 'actor', 'reason'))}"


def main(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "block-user":  # revoking sessions talks to the SuperTokens core
        from app.auth.supertokens_setup import init_supertokens
        from app.config import get_settings

        init_supertokens(get_settings())
    try:
        print(asyncio.run(_run(args)))
    except AppError as err:
        print(f"error: {err.message}", file=sys.stderr)
        sys.exit(1)
