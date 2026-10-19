"""Command line entry points: `python -m app.cli <command>`."""
import argparse
import asyncio
import subprocess
import sys

from app.db import get_sessionmaker


async def _seed(demo: bool) -> None:
    from app.seed import seed

    async with get_sessionmaker()() as session:
        await seed(session, demo=demo)
    print(f"seeded ({'demo' if demo else 'base'})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="alembic upgrade head")
    seed = sub.add_parser("seed", help="localities + plans (+ demo data with --demo)")
    seed.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        sys.exit(subprocess.call(["alembic", "upgrade", "head"]))
    if args.command == "seed":
        asyncio.run(_seed(args.demo))


if __name__ == "__main__":
    main()
