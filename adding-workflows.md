# How to Add a New Workflow

ResearchPilot didesain untuk mudah dikembangkan. Menambah workflow baru butuh 3 langkah.

## Langkah 1: Buat workflow file

Copy `backend/app/core/workflows/precedent_search.py` sebagai template.

Yang wajib ada:
- `async def run(target: str, progress: ProgressCallback) -> dict`
- Return dict dengan key: `analysis` (str), `target` (str), `validation` (dict)

```python
# backend/app/core/workflows/my_new_workflow.py

SYSTEM_PROMPT = """You are an expert in X..."""
USER_PROMPT = """..."""

async def run(target: str, progress=_noop) -> dict:
    await progress("scoping", 10, ...)
    # ... fetch data
    await progress("analyzing", 50, ...)
    analysis = await llm.complete(system=SYSTEM_PROMPT, user=...)
    await progress("done", 100, ...)
    return {"analysis": analysis, "target": target, "validation": ...}
```

## Langkah 2: Daftarkan di worker

Edit `backend/app/jobs/worker.py`:

```python
from app.core.workflows import my_new_workflow

async def run_my_new_workflow(ctx, run_id_str: str, target: str):
    # copy paste dari run_annual_report, ganti workflow module
    result = await my_new_workflow.run(target, progress=progress_cb)
    ...

class WorkerSettings:
    functions = [run_annual_report, run_my_new_workflow]  # tambah di sini
```

## Langkah 3: Expose di API

Edit `backend/app/api/routes/research.py` — tambahkan `workflow_type` mapping:

```python
WORKFLOW_MAP = {
    "annual_report": "run_annual_report",
    "competitive_landscape": "run_competitive_landscape",
    "my_new_workflow": "run_my_new_workflow",  # tambah di sini
}

# Di create_research():
job_fn = WORKFLOW_MAP.get(body.workflow_type, "run_annual_report")
await pool.enqueue_job(job_fn, str(run.id), body.target)
```

## Langkah 4 (optional): Tambahkan PPTX template

Edit `backend/app/exports/pptx.py` — fungsi `generate_pptx` sudah generic (pakai `executive_briefing` key). Kalau workflow baru menggunakan key `analysis` bukan `executive_briefing`, tambahkan fallback:

```python
briefing_text = result.get("executive_briefing") or result.get("analysis", "")
```

---

## Workflow yang sudah tersedia

| Workflow type | File | Terbaik untuk |
|--------------|------|---------------|
| `annual_report` | `annual_report.py` | Ringkas laporan tahunan + financial highlights |
| `competitive_landscape` | `competitive_landscape.py` | Map kompetitor + white space |
| `precedent_search` | `precedent_search.py` | Cari analogues M&A / fundraising / strategi |
| `industry_overview` | `industry_overview.py` | Primer industri untuk board/investor |

## Tips prompt design

1. **Beri struktur output eksplisit** — pakai `## Header` yang sama persis, supaya `BriefingRenderer` dan PPTX generator bisa parse
2. **Citation rules di system prompt** — selalu include instruksi citation format `[p.X]` atau `[Source: URL]`
3. **Temperature 0.2–0.3** untuk analisis faktual, **0.5–0.7** untuk synthesis/outlook
4. **Max tokens** — 5000 untuk focused outputs, 8000 untuk comprehensive primers
5. **Validate** — semua workflow harus melewati `validate_citations()` sebelum return
