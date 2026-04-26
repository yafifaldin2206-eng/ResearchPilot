# ResearchPilot

ResearchPilot is an open-source AI research tool that automates the kind of work a junior strategy consultant would do — finding annual reports, parsing them, and generating structured executive briefings. The output is a PowerPoint deck, not a chat response.

The core idea: instead of pasting a PDF into Claude and asking for a summary, ResearchPilot builds a full pipeline around the LLM — automated data acquisition, multi-step prompt chains, citation validation, and formatted export. The result is more reliable and consistent than a single prompt, and requires no manual work from the user beyond typing a company name.

## What it does

Four research workflows are currently supported:

**Annual Report Analysis** — given a company name or PDF URL, the system finds and downloads the annual report, parses it page by page (preserving page numbers for citations), and produces an eight-section executive briefing: executive summary, financial performance, strategic priorities, competitive positioning, risk factors, forward outlook, and critical gaps. Every factual claim is required to have a page citation; claims without citations are flagged.

**Competitive Landscape** — given a market description, the system searches for competitor data and produces a structured map of players, their positioning, and white space no current player occupies well.

**Precedent Search** — given a scenario (fundraising stage, business model, geography), the system finds analogous deals or strategic moves and synthesizes the pattern across them, including cautionary cases.

**Industry Overview** — a sector primer covering market sizing, value chain, competitive structure, regulatory environment, and a bull/base/bear outlook.

All workflows run as background jobs. Progress streams to the frontend in real time via SSE. Results can be downloaded as a .pptx file.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.12 |
| Database | Postgres 16 with pgvector |
| Queue | Redis + arq |
| LLM | Claude via Anthropic SDK |
| Search | Exa |
| Scraping | Playwright |
| Frontend | Next.js 15, Tailwind CSS |
| Auth | Clerk |
| Export | python-pptx |

## Running locally

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY and EXA_API_KEY at minimum

docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend playwright install chromium --with-deps
```

Open `http://localhost:3000`. With `APP_ENV=development`, authentication is bypassed — no Clerk setup needed for local testing.

For a first test, create a project, select Annual Report Analysis, and type a company name like `Bank Central Asia`. The run takes 2–3 minutes depending on the PDF size.

## API keys required

- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `EXA_API_KEY` — from dashboard.exa.ai (free tier available)
- `VOYAGE_API_KEY` — optional, only needed if you enable vector search features

See `docs/env-setup.md` for full deployment instructions including Railway and Vercel.

## How the pipeline works

```
user submits company name
  → backend enqueues arq job
  → worker: search for PDF URL (Exa)
  → worker: fetch and parse PDF (Playwright + pdfplumber)
  → worker: extract metadata via Claude
  → worker: generate executive briefing via Claude
  → worker: validate citations
  → frontend receives progress updates via SSE
  → user downloads .pptx
```

The citation validator checks that claims containing numbers, percentages, or financial figures have a corresponding page reference. Runs where citation coverage falls below the threshold are flagged in the UI.

## Project structure

```
researchpilot/
├── backend/
│   └── app/
│       ├── api/          HTTP layer (routes, schemas)
│       ├── core/         Workflow logic and prompt templates
│       ├── data/         Search, scraping, PDF parsing
│       ├── db/           Models and migrations
│       ├── exports/      PPTX generator
│       ├── jobs/         arq worker
│       └── llm/          Claude client and validators
├── frontend/
│   └── src/
│       ├── app/          Next.js App Router pages
│       ├── components/   UI primitives, research components
│       └── lib/          API client, utilities
├── infra/
│   ├── docker/           Postgres Dockerfile, nginx config
│   └── scripts/          DB seed and reset scripts
└── docs/
    ├── env-setup.md      Deployment guide
    └── adding-workflows.md  How to add a new workflow
```

## Adding a workflow

Copy an existing workflow file from `backend/app/core/workflows/`, implement the `run(target, progress)` function, register it in `backend/app/jobs/worker.py`, and add it to the workflow map in `backend/app/api/routes/research.py`. Full instructions in `docs/adding-workflows.md`.

## Known limitations

Annual reports that are scanned images (non-text PDFs) will not parse correctly. Some Indonesian company IR pages require scraping logic adjustments due to non-standard layouts. Rate limiting is not implemented. Test coverage is minimal.

## License

MIT
