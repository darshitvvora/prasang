"""Final review I1: messages queued inside the worker and the sweeper must start delivery on commit, not wait for a sweep."""
from app.workflows import starter as starter_module
from app.workflows.client import TemporalStarter
from app.workflows.starter import NoopStarter, get_starter, set_starter


async def test_sweep_process_installs_temporal_starter(monkeypatch):
    from app import cli

    seen = []

    async def fake_run_sweeps(session, starter):
        seen.append(type(get_starter()))
        return {}

    monkeypatch.setattr("app.sweeps.run_sweeps", fake_run_sweeps)
    set_starter(NoopStarter())
    try:
        await cli._sweep(None)
    finally:
        set_starter(NoopStarter())
    assert seen == [TemporalStarter]


def test_worker_process_installs_temporal_starter():
    from app.workflows import worker

    set_starter(NoopStarter())
    try:
        worker.configure_process()
        assert isinstance(starter_module.get_starter(), TemporalStarter)
    finally:
        set_starter(NoopStarter())
