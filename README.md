# platform-app-template

A [copier](https://copier.readthedocs.io/) template that scaffolds a new app
pre-wired to the [`platform-infra`](https://github.com/srainier/platform-infra)
shared infrastructure stack. Starting a new side project should take 5 minutes
of setup, not a day.

## What You Get

When you scaffold from this template, your new repo gets:

- **FastAPI backend** — fully typed, pyright strict, ruff lint/format, pytest
- **Per-app Pulumi infra** — creates a database on the shared cluster, wires up
  DigitalOcean App Platform, injects secrets
- **GitHub Actions** — `checks.yml` (PR: pyright, ruff, pytest) and
  `deploy.yml` (main: pulumi up + deploy)
- **Docs** — pre-filled README with architecture overview, local dev setup,
  env var docs, and SaaS dashboard links
- *(optional)* **Next.js frontend** — TypeScript strict, Biome linter
- *(optional)* **iOS app** — SwiftUI placeholder

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) installed
- [Pulumi Cloud](https://app.pulumi.com/) account (free tier is fine)
- [DigitalOcean](https://cloud.digitalocean.com/) account
- [platform-infra](https://github.com/srainier/platform-infra) deployed and
  stack outputs available at `srainier/platform-infra/prod`

## Usage

```bash
# 1. Install copier
uv tool install copier

# 2. Scaffold a new app
copier copy gh:srainier/platform-app-template ../my-new-app

# 3. Answer the prompts:
#   app_name:          my-new-app
#   app_display_name:  My New App
#   include_frontend:  yes/no
#   include_ios:       yes/no
#   github_handle:     srainier
#   pulumi_org:        srainier

# 4. Initialise git in the new repo
cd ../my-new-app
git init && git add . && git commit -m "chore: scaffold from platform-app-template"

# 5. Create the GitHub repo and push
gh repo create srainier/my-new-app --private --source=. --push

# 6. Add GitHub Actions secrets
gh secret set PULUMI_ACCESS_TOKEN --body "..."
gh secret set DIGITALOCEAN_TOKEN  --body "..."

# 7. Run SaaS setup (creates Flagsmith project, Sentry project, Honeycomb dataset)
export FLAGSMITH_SERVER_API_KEY=...
export SENTRY_AUTH_TOKEN=... SENTRY_ORG=...
export HONEYCOMB_API_KEY=...
bash scripts/setup-saas.sh
# Follow the printed instructions to add the remaining secrets

# 8. Deploy infrastructure
cd infra && pulumi stack init prod && pulumi up

# 9. Start building locally
cd ..
cp .env.example backend/.env   # pydantic-settings reads backend/.env
docker compose up -d
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

## Scaffold Prompts

| Prompt | Variable | Example |
|---|---|---|
| App slug (lowercase, hyphens) | `app_name` | `my-new-app` |
| Human-readable app name | `app_display_name` | `My New App` |
| Include Next.js frontend? | `include_frontend` | `yes` / `no` |
| Include iOS (SwiftUI) app? | `include_ios` | `yes` / `no` |
| GitHub username | `github_handle` | `srainier` |
| Pulumi org name | `pulumi_org` | `srainier` |

## Keeping Your App Up to Date

When this template is updated (e.g. a CI workflow is improved), you can pull
the changes into an existing app repo:

```bash
cd my-existing-app
copier update
```

Copier will show a diff and let you merge selectively — far better than a
permanent fork.

## Generated File Structure

```
my-new-app/
├── LICENSE
├── README.md
├── .gitignore
├── .env.example
├── compose.yaml                # local Postgres + Redis
├── .github/
│   └── workflows/
│       ├── checks.yml          # PR: pyright, ruff, pytest, build (frontend)
│       └── deploy.yml          # main: pulumi up
├── backend/
│   ├── pyproject.toml          # uv-managed, pyright strict, ruff, pytest
│   └── app/
│       ├── main.py             # FastAPI app
│       ├── config.py           # pydantic-settings
│       ├── db.py               # SQLAlchemy async engine
│       └── api/
│           └── health.py       # GET /health
│   └── tests/
│       └── test_health.py
├── infra/
│   ├── Pulumi.yaml
│   ├── Pulumi.prod.yaml
│   ├── pyproject.toml
│   ├── __main__.py
│   └── resources/
│       ├── platform.py         # StackReference → platform-infra
│       ├── config.py           # Pulumi secrets (Clerk, Flagsmith, Sentry, Honeycomb)
│       ├── database.py         # Creates DB on shared cluster
│       ├── app_platform.py     # DO App Platform service + VPC + all secrets
│       └── outputs.py
├── scripts/
│   └── setup-saas.sh           # Creates Flagsmith/Sentry/Honeycomb resources
├── frontend/                   # if include_frontend=yes
│   ├── package.json
│   ├── tsconfig.json           # strict
│   ├── biome.json
│   ├── next.config.ts          # output: "export" (static site)
│   └── app/
│       ├── layout.tsx
│       └── page.tsx
└── ios/                        # if include_ios=yes
    └── MyNewApp/
        ├── MyNewAppApp.swift
        └── ContentView.swift
```

## License

MIT — see [LICENSE](LICENSE).
