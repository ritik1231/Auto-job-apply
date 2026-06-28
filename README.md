# AI Job Application Assistant

A Chrome Extension that lets job seekers apply to recruiter hiring posts on LinkedIn in under 10 seconds.

Reads the visible post text → extracts structured job data via AI → matches your resume → generates a personalized email → sends via Gmail. No copy-paste. No tab-switching.

---

## Repository Structure

```
.
├── backend/          FastAPI application (Python 3.12+)
├── extension/        Chrome Extension MV3 (React + TypeScript)
├── phases.md         21 incremental implementation phases
├── system_design.md  Full architecture, API contracts, DB schema
├── decisions.md      Architecture Decision Records (ADRs)
└── CLAUDE.md         Project bible — conventions, principles, strategy
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12+ |
| Node.js | 20+ |
| Docker + Docker Compose | latest |
| Google Chrome | latest |

---

## Quick Start

### Backend

```bash
cd backend

# Create virtualenv and install deps
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Copy and fill in environment variables
cp .env.example .env

# Run tests (no tests yet in Phase 1 — just verify collection works)
python -m pytest

# Start the dev server (available from Phase 2)
uvicorn app.main:app --reload
```

### Extension

```bash
cd extension

# Install dependencies
npm install

# Copy and fill in environment variables
cp .env.example .env.local

# Start Vite dev server (extension loads from dist/)
npm run dev

# Type check
npm run typecheck

# Lint
npm run lint
```

### Load Extension in Chrome

1. Run `npm run build` in `extension/`
2. Open `chrome://extensions`
3. Enable **Developer mode**
4. Click **Load unpacked** → select `extension/dist/`

---

## Development Workflow

```
main          ← production-ready
develop       ← integration branch
feature/xxx   ← individual features (branch from develop)
fix/xxx       ← bug fixes
```

### Pre-commit Hooks

```bash
# Install hooks (one-time)
pre-commit install

# Run manually against all files
pre-commit run --all-files
```

### Commit Format

```
type(scope): short description

Body: explains WHY, not WHAT.
```

Types: `feat` `fix` `refactor` `test` `docs` `chore` `perf` `ci`

---

## Environment Variables

| File | Purpose |
|---|---|
| `backend/.env.example` | All backend env vars with descriptions |
| `extension/.env.example` | All extension env vars with descriptions |

Never commit `.env` files. All secrets stay out of version control.

---

## Architecture

See [`system_design.md`](system_design.md) for the full architecture with diagrams, API contracts, database schema, and folder structure.

Key points:
- **Clean Architecture**: Domain → Application → Infrastructure → Presentation
- **AI abstraction**: `IAIProvider` interface; Gemini is the MVP implementation
- **Zero scraping**: Content script reads visible DOM text only
- **Token security**: Gmail tokens are backend-only; the extension never sees them

---

## License

Private — all rights reserved.
