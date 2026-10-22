"""Command line entry points: `python -m app.cli <command>`."""
import argparse
import asyncio
import logging
import subprocess
import sys

from app.db import get_sessionmaker


async def _seed(demo: bool) -> None:
    from app.seed import seed

    async with get_sessionmaker()() as session:
        await seed(session, demo=demo)
    print(f"seeded ({'demo' if demo else 'base'})")


async def _reindex() -> None:
    from app.search.es import get_es
    from app.search.projector import reindex_all

    es = get_es()
    try:
        print(f"indexed {await reindex_all(get_sessionmaker(), es)} artists")
    finally:
        await es.close()


async def _create_index() -> None:
    from app.search.es import get_es
    from app.search.projector import ensure_index

    es = get_es()
    try:
        await ensure_index(es)
    finally:
        await es.close()


async def _project() -> None:
    from app.search.projector import run_projector

    await run_projector(get_sessionmaker())


async def _expire_leads() -> None:
    from app.leads.service import expire_leads

    async with get_sessionmaker()() as session:
        print(f"expired {await expire_leads(session)} leads")


async def _sweep(loop_seconds: int | None) -> None:
    from app.sweeps import run_sweeps
    from app.workflows.client import TemporalStarter
    from app.workflows.starter import set_starter

    starter = TemporalStarter()
    set_starter(starter)  # messages queued by the sweep start delivery on commit
    while True:
        try:
            async with get_sessionmaker()() as session:
                print(await run_sweeps(session, starter), flush=True)
        except Exception:
            logging.exception("sweep failed")
        if not loop_seconds:
            return
        await asyncio.sleep(loop_seconds)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["admin"]:
        from app.admin.cli import main as admin_main

        admin_main(argv[1:])
        return
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="alembic upgrade head")
    seed = sub.add_parser("seed", help="localities + plans (+ demo data with --demo)")
    seed.add_argument("--demo", action="store_true")
    sub.add_parser("create-index", help="create the Elasticsearch index + alias if missing")
    sub.add_parser("reindex", help="rebuild the Elasticsearch index from Postgres (alias swap)")
    sub.add_parser("project", help="run the outbox → Elasticsearch projector loop")
    sub.add_parser("expire-leads", help="mark past-dated new leads as expired")
    sweep = sub.add_parser("sweep", help="retry missed lead notifications, end overdue trials, lapse overdue subscriptions")
    sweep.add_argument("--loop", type=int, default=0, help="repeat every N seconds")
    sub.add_parser("admin", help="admin actions — see `admin --help`")
    sub.add_parser("msg91-templates", help="SMS/WhatsApp templates to register on DLT + MSG91, and which env vars are set")
    args = parser.parse_args(argv)

    if args.command == "msg91-templates":
        from app.config import get_settings
        from app.notifications.texts import template_report

        print(template_report(get_settings()))
    if args.command == "migrate":
        sys.exit(subprocess.call(["alembic", "upgrade", "head"]))
    if args.command == "seed":
        asyncio.run(_seed(args.demo))
    if args.command == "create-index":
        asyncio.run(_create_index())
    if args.command == "reindex":
        asyncio.run(_reindex())
    if args.command == "expire-leads":
        asyncio.run(_expire_leads())
    if args.command == "sweep":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        asyncio.run(_sweep(args.loop))
    if args.command == "project":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        asyncio.run(_project())


if __name__ == "__main__":
    main()
