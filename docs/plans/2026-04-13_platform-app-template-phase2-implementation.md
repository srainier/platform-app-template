> **Update 2026-06-06:** The platform now distinguishes infra-admin vs app-owner
> roles; apps are onboarded by the admin via `onboard-app.sh`. See platform-infra
> `docs/superpowers/specs/2026-06-06-platform-app-role-separation-design.md`.

# Phase 2 — `platform-app-template` Implementation Plan

## Context

`platform-infra` (Phase 1) has been implemented elsewhere and exports Pulumi stack outputs for shared DigitalOcean infrastructure (PostgreSQL, Redis, VPC). This repo becomes a **copier template** that scaffolds new app repos pre-wired to that shared stack. A developer runs one command, answers 6 prompts, and gets a CI-passing repo they can start coding in immediately. The goal is 5-minute project setup.

---

## Approach

Use **copier** (`_subdirectory: template` pattern) so all generated content lives in `template/`. Files needing Jinja2 rendering use `.jinja` suffix (stripped on output). Static files copied verbatim. Conditional `frontend/` and `ios/` directories are excluded via Jinja2 in `_exclude`.

---

## File Tree to Create

```
platform-app-template/
├── copier.yaml                                      # NEW — template config + 6 prompts
├── README.md                                        # REPLACE stub with usage instructions
└── template/
    ├── .gitignore.jinja
    ├── .env.example.jinja
    ├── LICENSE.jinja
    ├── README.md.jinja
    ├── .github/workflows/
    │   ├── checks.yml.jinja
    │   └── deploy.yml.jinja
    ├── backend/
    │   ├── pyproject.toml.jinja
    │   └── app/
    │       ├── __init__.py           # static
    │       ├── main.py.jinja
    │       ├── config.py             # static
    │       ├── db.py                 # static
    │       └── api/
    │           ├── __init__.py       # static
    │           └── health.py         # static
    │   └── tests/
    │       ├── __init__.py           # static
    │       ├── conftest.py           # static
    │       └── test_health.py        # static
    ├── infra/
    │   ├── __main__.py.jinja
    │   ├── Pulumi.yaml.jinja
    │   ├── Pulumi.prod.yaml.jinja
    │   ├── pyproject.toml.jinja
    │   └── resources/
    │       ├── __init__.py           # static
    │       ├── platform.py.jinja
    │       ├── database.py.jinja
    │       ├── app_platform.py.jinja
    │       ├── saas.py               # static (comments only)
    │       └── outputs.py.jinja
    ├── scripts/
    │   └── setup-saas.sh.jinja
    ├── frontend/                     # excluded when include_frontend=false
    │   ├── package.json.jinja
    │   ├── tsconfig.json             # static
    │   ├── biome.json                # static
    │   ├── next.config.ts            # static
    │   └── app/
    │       ├── layout.tsx.jinja
    │       └── page.tsx.jinja
    └── ios/                          # excluded when include_ios=false
        └── {{ app_class_name }}/
            ├── {{ app_class_name }}App.swift.jinja
            └── ContentView.swift.jinja
```

---

## Critical File Contents

### `copier.yaml`
```yaml
_subdirectory: template
_templates_suffix: .jinja
_exclude:
  - "{% if not include_frontend %}frontend/**{% endif %}"
  - "{% if not include_ios %}ios/**{% endif %}"

app_name:
  type: str
  help: "App slug — lowercase letters, digits, hyphens (e.g. my-cool-app)"
  validator: >-
    {% if not (app_name | regex_search('^[a-z][a-z0-9-]*$')) %}
    Must match ^[a-z][a-z0-9-]*$ (lowercase, hyphens only, must start with a letter)
    {% endif %}

app_display_name:
  type: str
  help: "Human-readable app name (e.g. My Cool App)"

include_frontend:
  type: bool
  help: "Include a Next.js frontend?"
  default: false

include_ios:
  type: bool
  help: "Include an iOS (SwiftUI) app?"
  default: false

github_handle:
  type: str
  help: "Your GitHub username (e.g. srainier)"

pulumi_org:
  type: str
  help: "Your Pulumi org name (e.g. srainier)"

# Computed — never prompted
app_class_name:
  type: str
  default: "{{ app_display_name | replace(' ', '') }}"
  when: false
```

Key patterns:
- `_exclude` renders empty string (ignored) when condition is false — safe no-op
- `app_class_name` via `when: false` computes PascalCase (e.g. `MyCoolApp`) for Swift class names
- `regex_search` is a built-in Jinja2 filter in copier 9.x

### `template/backend/pyproject.toml.jinja`
- `name = "{{ app_name }}"`, requires-python `>=3.12`
- deps: `fastapi[standard]>=0.115`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `pydantic-settings>=2.0`, `redis>=5.0`
- dev deps (in `[dependency-groups]`): `pytest>=8.0`, `pytest-asyncio>=0.24`, `httpx>=0.27`, `pyright>=1.1`, `ruff>=0.6`
- `[tool.pytest.ini_options] asyncio_mode = "auto"`
- `[tool.pyright] strict = true, pythonVersion = "3.12"`

### `template/backend/app/config.py` (static)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    database_url: str
    redis_url: str
    debug: bool = False
    environment: str = "production"

settings = Settings()
```

### `template/backend/app/db.py` (static)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

### `template/backend/app/api/health.py` (static)
```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
```

### `template/backend/tests/conftest.py` (static)
```python
import os
# Must be set BEFORE any app import — pydantic-settings reads at class instantiation
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
```

### `template/backend/tests/test_health.py` (static)
```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### `template/backend/app/main.py.jinja`
```python
from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="{{ app_display_name }}", version="0.1.0")
app.include_router(health_router)
```

### `template/infra/Pulumi.yaml.jinja`
```yaml
name: {{ app_name }}
description: "{{ app_display_name }} — per-app infrastructure"
runtime:
  name: python
  options:
    toolchain: uv
    virtualenv: .venv
```

### `template/infra/Pulumi.prod.yaml.jinja`
```yaml
config:
  {{ app_name }}:do_region: nyc3
  {{ app_name }}:environment: prod
```

### `template/infra/pyproject.toml.jinja`
- `name = "{{ app_name }}-infra"`, deps: `pulumi>=3.0`, `pulumi-digitalocean>=4.0`
- dev deps: `pyright>=1.1`, `ruff>=0.6`; pyright strict mode

### `template/infra/resources/platform.py.jinja`
```python
import pulumi

platform = pulumi.StackReference("{{ pulumi_org }}/platform-infra/prod")
postgres_host = platform.get_output("postgres_host")
postgres_port = platform.get_output("postgres_port")
postgres_admin_user = platform.get_output("postgres_admin_user")
postgres_admin_password = platform.get_output("postgres_admin_password")
postgres_cluster_id = platform.get_output("postgres_cluster_id")
redis_url = platform.get_output("redis_url")
vpc_id = platform.get_output("vpc_id")
do_region = platform.get_output("do_region")
```

### `template/infra/resources/database.py.jinja`
```python
import pulumi
import pulumi_digitalocean as do
from . import platform

db = do.DatabaseDb(
    "{{ app_name }}-db",
    cluster_id=platform.postgres_cluster_id,
    name="{{ app_name | replace('-', '_') }}",
)

db_user = do.DatabaseUser(
    "{{ app_name }}-db-user",
    cluster_id=platform.postgres_cluster_id,
    name="{{ app_name | replace('-', '_') }}_user",
)

database_url: pulumi.Output[str] = pulumi.Output.all(
    host=platform.postgres_host,
    port=platform.postgres_port,
    user=db_user.name,
    password=db_user.password,
    db=db.name,
).apply(
    lambda args: f"postgresql+asyncpg://{args['user']}:{args['password']}@{args['host']}:{args['port']}/{args['db']}"
)
```

### `template/infra/resources/app_platform.py.jinja`
```python
import pulumi
import pulumi_digitalocean as do
from . import database, platform

_service_envs = [
    do.AppSpecServiceEnvArgs(key="DATABASE_URL", value=database.database_url, type="SECRET"),
    do.AppSpecServiceEnvArgs(key="REDIS_URL", value=platform.redis_url, type="SECRET"),
]

_services = [
    do.AppSpecServiceArgs(
        name="api",
        environment_slug="python",
        github=do.AppSpecServiceGithubArgs(
            repo="{{ github_handle }}/{{ app_name }}", branch="main", deploy_on_push=True,
        ),
        source_dir="backend",
        run_command="uvicorn app.main:app --host 0.0.0.0 --port 8080",
        http_port=8080,
        instance_size_slug="apps-s-1vcpu-0.5gb",
        envs=_service_envs,
    )
]
{% if include_frontend %}
_static_sites = [
    do.AppSpecStaticSiteArgs(
        name="frontend",
        github=do.AppSpecServiceGithubArgs(
            repo="{{ github_handle }}/{{ app_name }}", branch="main", deploy_on_push=True,
        ),
        source_dir="frontend",
        build_command="npm run build",
        output_dir=".next",
    )
]
{% else %}
_static_sites: list[do.AppSpecStaticSiteArgs] = []
{% endif %}

app = do.App(
    "{{ app_name }}",
    spec=do.AppSpecArgs(
        name="{{ app_name }}",
        region=platform.do_region,
        services=_services,
        static_sites=_static_sites,
    ),
    opts=pulumi.ResourceOptions(depends_on=[database.db, database.db_user]),
)
```

### `template/infra/resources/outputs.py.jinja`
```python
import pulumi
from . import app_platform, database

pulumi.export("app_url", app_platform.app.live_url)
pulumi.export("database_name", database.db.name)
pulumi.export("database_user", database.db_user.name)
```

### `template/infra/__main__.py.jinja`
```python
# Pulumi registers resources as side effects of importing resource modules.
# Import order: platform → database → app_platform → outputs
from resources import (  # noqa: F401
    app_platform,
    database,
    outputs,
    platform,
    saas,
)
```

### `template/infra/resources/saas.py` (static)
Comments-only file documenting manual Clerk setup and scripted setup (Flagsmith, Sentry, Honeycomb) via `scripts/setup-saas.sh`.

### `template/scripts/setup-saas.sh.jinja`
Bash script that:
- Uses `curl` to create Flagsmith project, Sentry project, Honeycomb dataset via their REST APIs
- Prints API keys/DSNs to stdout for developer to save as GitHub secrets
- Skips gracefully if tokens not set in env
- Documents manual Clerk step (no reliable API for automation)

### `template/.github/workflows/checks.yml.jinja`
Jobs: `backend-typecheck` (pyright), `backend-lint` (ruff check + format), `backend-test` (pytest).
If `include_frontend`: add `frontend-typecheck` (tsc --noEmit) and `frontend-lint` (biome check).
No GitHub Actions `${{ }}` expressions needed in checks.yml.

### `template/.github/workflows/deploy.yml.jinja`
Trigger: `push to main`.
Jobs: `deploy-infra` (pulumi up --yes --stack prod).
If `include_frontend`: `deploy-frontend` job (npm ci, npm run build).

**Critical**: GitHub Actions `${{ secrets.FOO }}` must be escaped using `{% raw %}...{% endraw %}` blocks:
```yaml
{% raw %}
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
          DIGITALOCEAN_TOKEN: ${{ secrets.DIGITALOCEAN_TOKEN }}
{% endraw %}
```

### `template/frontend/package.json.jinja`
- `"name": "{{ app_name }}-frontend"`
- deps: `next: 15.x`, `react: ^19.0.0`, `react-dom: ^19.0.0`
- devDeps: `@biomejs/biome: ^1.9.0`, TypeScript + type defs
- scripts: `dev`, `build`, `start`, `lint` (biome), `typecheck` (tsc --noEmit)

### `template/frontend/app/layout.tsx.jinja`
Next.js root layout with `metadata.title = "{{ app_display_name }}"`.

### `template/frontend/app/page.tsx.jinja`
Minimal home page rendering `<h1>{{ app_display_name }}</h1>` with placeholder text.

### iOS files (both `.jinja`)
- `{{ app_class_name }}App.swift.jinja`: SwiftUI `@main` struct
- `ContentView.swift.jinja`: minimal VStack with `{{ app_display_name }}` text + `#Preview`

### Template repo `README.md` (replace stub)
Documents:
1. Prerequisites (`uv tool install copier`)
2. Usage: `copier copy gh:srainier/platform-app-template ../my-new-app`
3. The 6 prompts explained
4. Post-scaffold checklist (add GitHub secrets, run setup-saas.sh, `pulumi up`)
5. Template update: `copier update` in app repo
6. How to test the template locally

---

## Copier-Specific Gotchas

| Issue | Solution |
|---|---|
| GitHub Actions `${{ }}` conflicts with Jinja2 | Use `{% raw %}...{% endraw %}` around env blocks |
| Empty `_exclude` pattern when condition is true | Safe — empty strings ignored by copier's pathspec |
| `{{ app_class_name }}` in directory names on disk | Valid on Linux/macOS; git handles `{` `}` in filenames |
| `when: false` vs `when: "false"` | Use boolean `false`, not string |
| `asyncio_mode = "auto"` eliminates most `@pytest.mark.asyncio` | Still add decorator on tests for explicitness |
| `conftest.py` must set env vars before app import | `os.environ.setdefault(...)` at module top level (before any app import) |
| pydantic strict typing in `db.py` | Import `AsyncGenerator` from `collections.abc` not `typing` |

---

## Implementation Order

1. `copier.yaml` (establishes all variable names)
2. `template/backend/` static files (config.py, db.py, health.py, conftest.py, test_health.py)
3. `template/backend/` jinja files (pyproject.toml.jinja, main.py.jinja)
4. `template/infra/resources/` in dependency order: platform → database → app_platform → saas → outputs
5. `template/infra/__main__.py.jinja`, Pulumi.yaml.jinja, Pulumi.prod.yaml.jinja, pyproject.toml.jinja
6. `template/scripts/setup-saas.sh.jinja`
7. `template/.github/workflows/` (most complex — last)
8. `template/frontend/` and `template/ios/` conditional files
9. `template/.gitignore.jinja`, `.env.example.jinja`, `LICENSE.jinja`, `README.md.jinja`
10. Template repo `README.md` (replace stub)

---

## Verification

1. Install copier: `uv tool install copier`
2. Run scaffold with all options: `copier copy /home/user/platform-app-template /tmp/test-app` — answer prompts with `include_frontend=true, include_ios=true`
3. Verify output structure matches the plan's "What Gets Scaffolded" section
4. In `/tmp/test-app/backend`: `uv sync && uv run pytest` — all tests should pass
5. In `/tmp/test-app/backend`: `uv run pyright && uv run ruff check .` — no errors
6. Re-run with `include_frontend=false, include_ios=false` — verify `frontend/` and `ios/` absent
7. Verify GitHub Actions workflow YAML is syntactically valid (no unescaped `${{ }}`)
8. Verify copier update workflow: make a change to the template, run `copier update` in test-app — changes should apply cleanly
