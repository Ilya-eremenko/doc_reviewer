from collections.abc import Callable
from uuid import UUID

from redis import Redis
from rq import Queue

from app.core.config import get_settings


ANALYSIS_QUEUE_NAME = "analysis"
RUN_ANALYSIS_JOB_PATH = "jobs.run_analysis.run_analysis"

RunAnalysisEnqueue = Callable[[UUID], None]


def enqueue_run_analysis(analysis_id: UUID) -> None:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(ANALYSIS_QUEUE_NAME, connection=connection)
    queue.enqueue_call(func=RUN_ANALYSIS_JOB_PATH, args=(str(analysis_id),), timeout=1800, result_ttl=3600)
