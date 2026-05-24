# AI Company — Autonomous Software Company

> From idea to a real GitLab repository with production code — in under 3 minutes. Powered by Gemini 2.5 Flash.

## Live Demo
**App:** https://ai-company-ylpszbenla-uc.a.run.app

**GitLab:** https://gitlab.com/suryahackathon-cyber

**GitHub:** https://github.com/suryahackathon-cyber/ai-company

---

## What It Does

AI Company is an autonomous software company powered by Gemini 2.5 Flash. Give it any project idea and it:

1. **Plans** — 6 specialist AI agents analyze your project simultaneously
2. **Estimates** — timeline, team size, cost, risks
3. **Generates Code** — real production-quality code files
4. **Creates GitLab repo** — with files, issues, and sprint milestones
5. **Optimizes** — budget optimizer and workforce planner

## Features

- **6 AI Agents** — PM, Architect, Dev, QA, DevOps, Marketing
- **CEO Mode** — one-page executive pitch with KPIs and GTM strategy
- **Team Meeting** — agents debate trade-offs in real time
- **Build This App** — generates real code (server.js, schema.sql, App.js, docker-compose, README)
- **Push to GitLab** — creates real repo with issues and Sprint 1 milestone
- **Budget Optimizer** — slider to reduce cost by 10-70% with AI renegotiation
- **Workforce Planner** — add 1-5 developers and see timeline/cost impact with Brooks Law analysis
- **Past Projects** — Firestore memory stores all projects for instant rerun
- **AI Observability** — Arize monitors every Gemini API call

## Partner Integrations

| Partner | How Used |
|---------|----------|
| **GitLab** | Creates repos, pushes code files, creates issues, sprint milestones |
| **Firestore (GCP)** | Stores all project plans for agent memory across sessions |
| **Arize** | Logs every Gemini API call — latency, prompts, responses |

## Tech Stack

- **AI:** Gemini 2.5 Flash via Google Gen AI SDK
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla HTML/CSS/JS
- **Database:** Google Firestore
- **Deployment:** Google Cloud Run
- **Observability:** Arize AI

## Architecture
User Input
↓
Orchestrator (Gemini 2.5 Flash)
↓
┌─────────────────────────────────────────┐
│ PM │ Architect │ Dev │ QA │ DevOps │ Mkt │
└─────────────────────────────────────────┘
↓              ↓           ↓
GitLab         Firestore    Arize
(repos)        (memory)     (observability)
## Running Locally

```bash
# Clone
git clone https://github.com/suryahackathon-cyber/ai-company
cd ai-company/backend

# Install
pip install -r requirements.txt

# Set env vars
cp .env.example .env
# Edit .env with your keys

# Run
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Environment Variables
GOOGLE_API_KEY=your_gemini_api_key
GITLAB_TOKEN=your_gitlab_token
GITLAB_USERNAME=your_gitlab_username
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_github_username
ARIZE_API_KEY=your_arize_key
ARIZE_SPACE_ID=your_arize_space_id
## License

MIT License — see LICENSE file
