"""Research routes — trigger jobs, get status, stream progress."""
import asyncio
import json
import uuid
from typing import Annotated, AsyncIterator, Literal
from arq.connections import create_pool, RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from pydantic import BaseModel

from app.auth import CurrentUser, get_user_id
from app.config import settings
from app.db.session import get_db
from app.db.models import ResearchRun, Project
from app.api.schemas.research import ResearchOut

router = APIRouter()

WorkflowType = Literal["annual_report", "competitive_landscape", "precedent_search", "industry_overview"]

WORKFLOW_JOB_MAP: dict[WorkflowType, str] = {
    "annual_report":        "run_annual_report",
    "competitive_landscape":"run_competitive_landscape",
    "precedent_search":     "run_precedent_search",
    "industry_overview":    "run_industry_overview",
}

WORKFLOW_LABELS: dict[WorkflowType, str] = {
    "annual_report":         "Annual Report Analysis",
    "competitive_landscape": "Competitive Landscape",
    "precedent_search":      "Precedent Search",
    "industry_overview":     "Industry Overview",
}


class ResearchCreate(BaseModel):
    project_id: uuid.UUID
    target: str
    workflow_type: WorkflowType = "annual_report"


async def _verify_project_access(project_id: uuid.UUID, user_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(404, "Project not found")
    return project


@router.post("", response_model=ResearchOut)
async def create_research(
    body: ResearchCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = get_user_id(user)
    await _verify_project_access(body.project_id, user_id, db)

    run = ResearchRun(
        project_id=body.project_id,
        workflow_type=body.workflow_type,
        target=body.target,
        status="pending",
        progress={"step": "queued", "pct": 0},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job_fn = WORKFLOW_JOB_MAP[body.workflow_type]
    await pool.enqueue_job(job_fn, str(run.id), body.target)
    await pool.close()

    return run


@router.get("/{run_id}", response_model=ResearchOut)
async def get_research(
    run_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != get_user_id(user):
        raise HTTPException(404, "Run not found")
    return run


@router.get("/by-project/{project_id}", response_model=list[ResearchOut])
async def list_research_by_project(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = get_user_id(user)
    await _verify_project_access(project_id, user_id, db)
    result = await db.execute(
        select(ResearchRun)
        .where(ResearchRun.project_id == project_id)
        .order_by(ResearchRun.created_at.desc())
    )
    return result.scalars().all()


async def _sse_stream(run_id: uuid.UUID) -> AsyncIterator[dict]:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    channel = f"run:{run_id}"
    await pubsub.subscribe(channel)
    try:
        yield {"event": "ping", "data": json.dumps({"connected": True})}
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            try:
                parsed = json.loads(data)
                yield {"event": "progress", "data": data}
                if parsed.get("step") in ("done", "error") or parsed.get("pct") == 100:
                    break
            except json.JSONDecodeError:
                continue
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.close()


@router.get("/{run_id}/stream")
async def stream_research(
    run_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != get_user_id(user):
        raise HTTPException(404, "Run not found")
    return EventSourceResponse(_sse_stream(run_id))


@router.get("/workflows/list")
async def list_workflows():
    """Return available workflow types for the frontend selector."""
    return [
        {"value": k, "label": v}
        for k, v in WORKFLOW_LABELS.items()
    ]
