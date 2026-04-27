"""arq background worker — all four workflows."""
import json
import uuid
from datetime import datetime, timezone
from arq.connections import RedisSettings
import structlog

from app.config import settings
from app.db.session import SessionLocal
from app.db.models import ResearchRun
from app.core.workflows import annual_report, competitive_landscape, precedent_search, industry_overview

logger = structlog.get_logger()


async def _update_progress(ctx, run_id: uuid.UUID, step: str, pct: int, detail: dict | None = None):
    progress_data = {"step": step, "pct": pct, "detail": detail or {}}
    async with SessionLocal() as session:
        run = await session.get(ResearchRun, run_id)
        if run:
            run.progress = progress_data
            await session.commit()
    await ctx["redis"].publish(f"run:{run_id}", json.dumps(progress_data))


async def _execute_workflow(ctx, run_id_str: str, target: str, workflow_fn):
    run_id = uuid.UUID(run_id_str)
    logger.info("job_start", run_id=run_id_str, target=target)

    async with SessionLocal() as session:
        run = await session.get(ResearchRun, run_id)
        if not run:
            logger.error("run_not_found", run_id=run_id_str)
            return
        run.status = "running"
        await session.commit()

    async def progress_cb(step: str, pct: int, detail: dict | None = None):
        await _update_progress(ctx, run_id, step, pct, detail)

    try:
        result = await workflow_fn(target, progress=progress_cb)
        async with SessionLocal() as session:
            run = await session.get(ResearchRun, run_id)
            run.status = "done"
            run.result = result
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
        await ctx["redis"].publish(
            f"run:{run_id}",
            json.dumps({"step": "done", "pct": 100, "detail": {"complete": True}}),
        )
        logger.info("job_complete", run_id=run_id_str)

    except Exception as e:
        logger.exception("job_failed", run_id=run_id_str)
        async with SessionLocal() as session:
            run = await session.get(ResearchRun, run_id)
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
        await ctx["redis"].publish(
            f"run:{run_id}",
            json.dumps({"step": "error", "pct": 0, "detail": {"error": str(e)}}),
        )


async def run_annual_report(ctx, run_id_str: str, target: str):
    await _execute_workflow(ctx, run_id_str, target, annual_report.run)

async def run_competitive_landscape(ctx, run_id_str: str, target: str):
    await _execute_workflow(ctx, run_id_str, target, competitive_landscape.run)

async def run_precedent_search(ctx, run_id_str: str, target: str):
    await _execute_workflow(ctx, run_id_str, target, precedent_search.run)

async def run_industry_overview(ctx, run_id_str: str, target: str):
    await _execute_workflow(ctx, run_id_str, target, industry_overview.run)


class WorkerSettings:
    functions = [run_annual_report, run_competitive_landscape, run_precedent_search, run_industry_overview]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 600
    max_jobs = 5
