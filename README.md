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
- [Pulumi Cloud](https://app.pulumi.com/) account — ask the platform admin to add
  you to the `app-owners` team, which grants **Read** on `platform-infra/prod`
  (needed for the `StackReference`). You create and own your own app stack — you
  get **Admin** on it automatically when you run `pulumi stack init`
- A scoped **`app-deployer`** DigitalOcean token — issued by the platform admin
  (see platform-infra →
  ["Granting a new app-owner"](https://github.com/srainier/platform-infra#granting-a-new-app-owner)).
  Pulumi reads it only from `DIGITALOCEAN_TOKEN` (doctl contexts don't carry
  over, and doctl can't show a saved token again), so keep it in a file:
  ```bash
  mkdir -p ~/.config/platform && chmod 700 ~/.config/platform
  (umask 077; pbpaste > ~/.config/platform/app-deployer.token)   # after copying the token
  ```
- [platform-infra](https://github.com/srainier/platform-infra) deployed and
  stack outputs available at `srainier/platform-infra/prod`

## Usage

```bash
# 1. Install copier
uv tool install copier

# 2. Scaffold a new app (run from the folder that should contain it)
copier copy --trust gh:srainier/platform-app-template ./my-new-app
#    (--trust lets the template run `uv lock` for backend/ and infra/; DO
#    App Platform needs the committed uv.lock to detect the Python build)

# 3. Answer the prompts:
#   app_name:          my-new-app
#   app_display_name:  My New App
#   include_frontend:  yes/no
#   include_ios:       yes/no
#   github_handle:     srainier
#   pulumi_org:        srainier

# 4. Initialise git in the new repo
cd my-new-app
git init && git add . && git commit -m "chore: scaffold from platform-app-template"

# 5. Create the GitHub repo and push
gh repo create srainier/my-new-app --private --source=. --push
#    The push runs the Deploy workflow, which skips with a warning until the
#    step-8 secrets exist. That's expected.

# 6. If the repo is private, grant DigitalOcean's GitHub app access to it.
#    Stop on DigitalOcean's create-app page; Pulumi creates the app.

# 7. Run the generated preflight checklist (checks GitHub, Pulumi access to
#    platform-infra, the DO token, and which Actions secrets are set)
bash scripts/preflight-new-app.sh

# 8. Add GitHub Actions secrets (use your app-deployer DO token, NOT an admin token)
# (copy each token, then run its line; see docs/credentials.md)
pbpaste | gh secret set PULUMI_ACCESS_TOKEN   # dedicated Pulumi access token
gh secret set DIGITALOCEAN_TOKEN < ~/.config/platform/app-deployer.token

# 9. Create the SaaS resources and collect five values: Clerk publishable +
#    secret key, Flagsmith server-side key, Sentry DSN, Honeycomb ingest key.
#    Follow docs/credentials.md: each service shows look-alike keys, and it
#    lists exactly which one to copy. (scripts/setup-saas.sh can pre-create
#    Flagsmith/Sentry/Honeycomb projects, but you still copy keys from the UIs.)

# 10. Initialise your app stack, then store each value as Pulumi config.
#     Copy a value in the vendor UI, then run its line (keeps secrets out of
#     shell history). The committed infra/Pulumi.prod.yaml holds them encrypted.
cd infra
pulumi stack init prod   # first time only — you create and own this stack
pbpaste | pulumi config set clerk_publishable_key            # pk_test_...
pbpaste | pulumi config set --secret clerk_secret_key        # sk_test_...
pbpaste | pulumi config set --secret flagsmith_api_key       # ser....
pbpaste | pulumi config set --secret sentry_dsn              # https://...@...sentry.io/...
pbpaste | pulumi config set --secret honeycomb_api_key       # hcaik_... (64 chars)
git add Pulumi.prod.yaml && git commit -m "chore: prod config" && git push
#     (values are encrypted; CI's `pulumi up` reads this file)

# 11. Deploy infrastructure (creates your app + per-app database/user/pool)
export DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)"
pulumi up   # already inside infra/ from step 10; takes ~4 minutes
# The app deploys and serves, but /api/health reports "database": "waiting"
# until onboarding (step 12): it can't reach the shared cluster yet.

# 12. Ask the platform admin to onboard your app (one-time, run in platform-infra):
#     ./scripts/onboard-app.sh my-new-app
#   This registers your app as a trusted source on the shared clusters and grants
#   your DB user schema privileges. See platform-infra → "Onboarding a new app".

# 13. Nothing to redeploy: the app retries the database and connects on its
#     own within about a minute of onboarding. Check it:
curl -s "$(pulumi stack output app_url)/api/health"   # "database": "ready"
#     (Apps generated before this behaviour need a redeploy here:
#      doctl apps create-deployment "$(pulumi stack output app_id)". A plain
#      `pulumi up` does NOT redeploy when nothing changed.)

# 14. Verify live (health incl. database, flag, auth; exits non-zero on failure)
cd ..
bash scripts/verify-live.sh

# 15. Start building locally
bash scripts/dev-env.sh                # backend/.env (+ frontend/.env.local) with dev keys from Pulumi config
docker compose up -d --wait            # local Postgres + Valkey from compose.yaml
cd backend && uv sync && uv run uvicorn app.main:app --reload    # http://localhost:8000/api/health
# second terminal, from the repo root (frontend apps only):
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## Tearing an app down

The `app-deployer` token can delete the App but not the database, user or pool
(no `database:delete` scope, by design), so `pulumi destroy` must run with the
admin token:

```bash
cd infra
DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/do-admin.token)" pulumi destroy
pulumi stack rm prod
```

Then open a platform-infra PR removing the app's UUID from `trusted_app_ids`
(after the destroy, not before), delete the GitHub repo, and delete the app's
Clerk application, Flagsmith server-side key, Sentry project and Honeycomb
ingest key. Keep the shared `hello_banner` flag.

## Troubleshooting

- **`pulumi refresh` makes the next `up` redeploy the app.** DigitalOcean
  returns service env vars in its own order, so after a refresh every env var
  looks changed. Run `pulumi up` once and it settles. Avoid refreshing unless
  you need to.
- **`verify-live.sh` says there's no live URL.** `app_url` is captured at
  `pulumi up` time. Export `DIGITALOCEAN_TOKEN` and the script looks the URL up
  from DigitalOcean instead.

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
├── .env.example                # full env reference
├── compose.yaml                # local Postgres + Valkey
├── .github/
│   └── workflows/
│       ├── checks.yml          # PR: pyright, ruff, pytest, build (frontend)
│       └── deploy.yml          # main: pulumi up
├── backend/
│   ├── .env.example            # copy to backend/.env for local backend
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
│       ├── app_platform.py     # DO App Platform service + static site + all secrets
│       └── outputs.py
├── scripts/
│   ├── preflight-new-app.sh    # Checks repo/auth and prints credential checklist
│   ├── setup-saas.sh           # Assists Flagsmith/Sentry/Honeycomb setup
│   ├── verify-live.sh          # Curls app_url /api and /feature
│   └── dev-env.sh              # Fills local env files from Pulumi config
├── frontend/                   # if include_frontend=yes
│   ├── .env.example            # copy to frontend/.env.local
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
