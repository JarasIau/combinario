from types import SimpleNamespace
from typing import Any

import pytest
from arq.jobs import JobStatus

import services.jobs as jobs_module
from services.jobs import JobNotFoundError, JobResultError, JobService


class FakeJob:
    def __init__(
        self,
        job_id: str,
        redis: object,
        status: JobStatus,
        result: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.job_id = job_id
        self.redis = redis
        self._status = status
        self._result = result
        self._error = error

    async def status(self) -> JobStatus:
        return self._status

    async def result(self) -> object:
        if self._error is not None:
            raise self._error
        return self._result


def patch_job(monkeypatch: pytest.MonkeyPatch, fake_job: FakeJob) -> None:
    def job_factory(job_id: str, redis: object, **_: Any) -> FakeJob:
        assert job_id == fake_job.job_id
        assert redis is fake_job.redis
        return fake_job

    monkeypatch.setattr(jobs_module, "Job", job_factory)


@pytest.mark.asyncio
async def test_fetch_returns_incomplete_status(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = object()
    patch_job(monkeypatch, FakeJob("job-123", redis, JobStatus.queued))

    result = await JobService(redis).fetch("job-123")

    assert result.status == "queued"
    assert result.item is None


@pytest.mark.asyncio
async def test_fetch_returns_completed_item(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = object()
    item = SimpleNamespace(id=3, emoji="💨", text="Steam", parents=[])
    patch_job(monkeypatch, FakeJob("job-123", redis, JobStatus.complete, item))

    result = await JobService(redis).fetch("job-123")

    assert result.status == "complete"
    assert result.item is not None
    assert result.item.text == "Steam"


@pytest.mark.asyncio
async def test_fetch_raises_for_missing_job(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = object()
    patch_job(monkeypatch, FakeJob("job-123", redis, JobStatus.not_found))

    with pytest.raises(JobNotFoundError):
        await JobService(redis).fetch("job-123")


@pytest.mark.asyncio
async def test_fetch_wraps_result_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = object()
    patch_job(
        monkeypatch,
        FakeJob("job-123", redis, JobStatus.complete, error=RuntimeError("boom")),
    )

    with pytest.raises(JobResultError):
        await JobService(redis).fetch("job-123")
