import logging
from typing import Any

from arq.jobs import Job, JobStatus

from schemas.item import ItemSchema
from schemas.task import TaskResponse

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    pass


class JobResultError(Exception):
    pass


class JobService:
    def __init__(self, arq_pool: Any):
        self.arq_pool = arq_pool

    async def fetch(self, job_id: str) -> TaskResponse:
        job = Job(job_id=job_id, redis=self.arq_pool)
        status = await job.status()

        if status == JobStatus.not_found:
            raise JobNotFoundError(job_id)

        if status != JobStatus.complete:
            return TaskResponse(status=status.value)

        try:
            item = ItemSchema.model_validate(await job.result())
        except Exception as exc:
            logger.error("Failed to retrieve result for job %s: %s", job_id, exc)
            raise JobResultError(job_id) from exc

        return TaskResponse(status="complete", item=item)
