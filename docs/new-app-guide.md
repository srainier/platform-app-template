# New app on the platform

Follow this guide, or hand it to an agent, and you end up with a new app
generated from `platform-app-template`, in its own GitHub repo, running on the
shared `platform-infra` stack with sign-in, a database, a feature flag, error
reporting and tracing all working.

It's written so an agent can run every step after **Step 0** without asking,
and so a person can follow it by hand. Steps carry a tag saying who does them:

| Tag | Who | Why |
|---|---|---|
| **[you]** | the person starting the app | vendor web UIs, tokens, anything that needs a login |
| **[admin]** | the platform admin (may be you) | changes to shared infrastructure |
| **[agent]** | an agent or you at a terminal | everything scriptable |

Every **[agent]** phase ends with a **Checkpoint**. Don't start the next phase
until the checkpoint passes. If it fails, look in [Known problems](#known-problems).

Rules for agents:

- Never print, log, echo or commit a secret. Read tokens from the files in
  `~/.config/platform/`, only inside the command that needs them.
- Never run `pulumi up` on `platform-infra` yourself. Only `onboard-app.sh` does
  that, and only the admin runs it.
- Don't run `pulumi refresh` on the app stack unless a step says to (it causes a
  one-off redeploy; see Known problems).
- Don't delete cloud, GitHub or SaaS resources. Teardown is a separate, human
  decision.

This guide was proven end to end with `hello-verify` (October 2026). It assumes
a template version that includes PR #9 (the app comes up before onboarding).

---

## Step 0: collect everything up front [you]

This is all the manual work. Do it once at the start and the rest can run
unattended, apart from the admin's onboarding in Phase 6. Budget about 30
minutes the first time and 15 for later apps.

### 0.1 Once per person (skip what you've already done)

1. **Tools**, installed and logged in: `uv`, `copier` (`uv tool install copier`),
   `pulumi` (`pulumi login`), `gh` (`gh auth login`), Node 24, Docker (for
   local dev), and `git` with SSH access to GitHub. The admin also needs
   `psql` (on macOS: `brew install libpq`).
2. **Pulumi access** [admin]: add the person to the `app-owners` team, which
   gets **Read** on `platform-infra/prod` (platform-infra README, "Granting a
   new app-owner").
3. **DigitalOcean `app-deployer` token** [admin issues, you store]: custom
   scopes `app` create/read/update/delete and `database` create/read. Save it
   where Pulumi and the scripts can find it:
   ```bash
   mkdir -p ~/.config/platform && chmod 700 ~/.config/platform
   (umask 077; pbpaste > ~/.config/platform/app-deployer.token)   # after copying it
   ```
   The admin also keeps a full-access token in
   `~/.config/platform/do-admin.token` for onboarding and teardown only.
4. **DigitalOcean's GitHub app** can see your repos: GitHub → Settings →
   Applications → Installed GitHub Apps → DigitalOcean → Configure. Choosing
   **All repositories** removes this step for every future app. Otherwise
   you'll add each new repo after Phase 2.
5. **Pulumi token for CI**: Pulumi Cloud → avatar → Personal access tokens →
   Create. Store it next to the DO token:
   ```bash
   (umask 077; pbpaste > ~/.config/platform/pulumi-ci.token)
   ```
   One token can serve all your app repos.

### 0.2 Decide the app's identity

| Answer | Rule | Example |
|---|---|---|
| `APP` (slug) | `^[a-z][a-z0-9-]*[a-z0-9]$`; not already a GitHub repo, Pulumi project or DO app | `my-new-app` |
| Display name | anything | `My New App` |
| Frontend? | yes or no | yes |
| iOS? | yes or no | no |

### 0.3 Create the SaaS resources and hand off five values

Follow [credentials.md](credentials.md) for the click paths and the
**Copy this / Not these** tables. Each vendor shows look-alike keys:

1. **Clerk**: create an application named after the app (Development
   instance). You get a `pk_test_…` publishable key and an `sk_test_…` secret
   key.
2. **Flagsmith**: in the shared project, **Production** environment, create a
   **server-side** environment key named `<APP>-backend` (`ser.…`). Don't create
   a flag; `hello_banner` already exists and is shared by all apps.
3. **Sentry**: create a **FastAPI** project named `<APP>`. Copy its DSN.
4. **Honeycomb**: in the `prod` environment, create an **ingest** key named
   `<APP>`. Copy the 64-character value from the dialog; it's shown only once.

Put the five values in a private hand-off file named after **your** app's slug
(`~/.config/platform/apps/<your-app-slug>.env`). Phase 4 loads it into Pulumi
config and then you delete it:

```bash
APP=<your-app-slug>          # replace with your slug from 0.2, e.g. hello-accept
mkdir -p ~/.config/platform/apps
(umask 077; cat > ~/.config/platform/apps/$APP.env <<'EOF'
CLERK_PUBLISHABLE_KEY=''
CLERK_SECRET_KEY=''
FLAGSMITH_API_KEY=''
SENTRY_DSN=''
HONEYCOMB_API_KEY=''
EOF
)
open -e ~/.config/platform/apps/$APP.env   # or any plain-text editor: paste each value between its quotes, save
```

Leave out `CLERK_PUBLISHABLE_KEY` for an app without a frontend.

### 0.4 Line up the admin

Phase 6 needs the platform admin for about 5 minutes. They run one script and
merge one PR. If you are the admin, the agent can run Phase 6 too, given
`~/.config/platform/do-admin.token`. Agree up front whether it may merge the
PR.

### 0.5 Hand-off checklist (give this to the agent)

```text
APP=<slug>  DISPLAY="<display name>"  FRONTEND=<true|false>  IOS=<true|false>
GITHUB_OWNER=srainier  PULUMI_ORG=srainier
~/.config/platform/app-deployer.token     present (chmod 600)
~/.config/platform/pulumi-ci.token        present (chmod 600)
~/.config/platform/apps/$APP.env          present (chmod 600), five values
DigitalOcean GitHub app                   All repositories / or add the repo after Phase 2
Admin for Phase 6                         <name>; agent may / may not run onboarding and merge
```

What an agent **can't** do, so these stay with people: anything in a vendor
web UI (0.3), creating tokens (0.1), granting the GitHub app access to a repo,
signing in to the app in a browser (Phase 7), and looking at the Sentry and
Honeycomb dashboards, unless you also hand over read tokens for them.

---

## Phase 1: preconditions [agent]

```bash
APP=<your-app-slug>          # replace with your slug from 0.2, e.g. hello-accept
for f in app-deployer pulumi-ci; do test -s ~/.config/platform/$f.token || echo "missing $f.token"; done
test -s ~/.config/platform/apps/$APP.env || echo "missing hand-off file"
pulumi whoami && gh auth status && uv --version && copier --version
pulumi stack output do_region --stack srainier/platform-infra/prod   # read access to the platform
gh repo view srainier/$APP 2>&1 | grep -q 'Could not resolve' && echo "repo name free"
pulumi project ls 2>/dev/null | grep -q "^  $APP " && echo "PULUMI PROJECT EXISTS: pick another name"
```

**Checkpoint:** nothing reported missing, `do_region` prints `nyc3`, and the
repo name is free.

## Phase 2: scaffold and create the repo [agent]

```bash
cd ~/mini   # the folder that should contain the app
copier copy --trust gh:srainier/platform-app-template ./$APP \
  -d app_name=$APP -d "app_display_name=<Your Display Name>" \
  -d include_frontend=true -d include_ios=false \
  -d github_handle=srainier -d pulumi_org=srainier
cd $APP
git init -q && git add . && git commit -qm "chore: scaffold from platform-app-template"
gh repo create srainier/$APP --private --source=. --push
```

The push starts the Deploy workflow. It skips with a warning until Phase 3's
secrets exist. That's expected.

**Checkpoint:** `.copier-answers.yml` exists and records `_commit`, and both
`backend/uv.lock` and `infra/uv.lock` exist. If 0.1 step 4 isn't set to "All
repositories", ask the person to add this repo to the DigitalOcean GitHub app now.

## Phase 3: GitHub Actions secrets [agent]

```bash
gh secret set PULUMI_ACCESS_TOKEN < ~/.config/platform/pulumi-ci.token
gh secret set DIGITALOCEAN_TOKEN  < ~/.config/platform/app-deployer.token
DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)" bash scripts/preflight-new-app.sh
```

**Checkpoint:** preflight ends with `Preflight complete.` and lists both
secrets as `set`.

## Phase 4: stack and config [agent]

```bash
cd infra && pulumi stack init prod && cd ..
bash scripts/load-config.sh      # reads ~/.config/platform/apps/$APP.env
bash scripts/check-config.sh     # formats + read-only vendor calls; prints no values
git add infra/Pulumi.prod.yaml && git commit -qm "chore: prod config (encrypted)" && git push
```

**Checkpoint:** every `check-config.sh` line says `ok`, and `git show
--stat HEAD` lists only `infra/Pulumi.prod.yaml`. If a line says FAIL, the
person fixes that value in the hand-off file (credentials.md says which key is
which), then re-run both scripts. When it passes, delete the hand-off file:
`rm ~/.config/platform/apps/$APP.env`.

## Phase 5: deploy [agent]

```bash
cd infra
DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)" pulumi up --yes   # ~4 min
curl -s "$(pulumi stack output app_url)/api/health"
```

**Checkpoint:** `pulumi up` creates 5 resources with no errors, and health returns
`{"status":"ok","database":"waiting"}`. "Waiting" is correct: the app can't
reach the shared database until Phase 6.

## Phase 6: onboarding [admin]

Run in `platform-infra`, on a clean `main`:

```bash
cd ~/mini/platform-infra && git switch main && git pull --ff-only
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
export DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/do-admin.token)"
pulumi preview --stack prod --refresh    # expect "0 to update" (uuid/createdAt output drift is normal)
./scripts/onboard-app.sh $APP
```

Then run the `git switch -c … / gh pr create …` lines the script prints, and
**merge that PR right away**. Until it's on `main`, any platform-infra CI run
removes the app from the firewalls.

**Checkpoint:** the script ends with `Done.`, the PR is merged, the
platform-infra `Pulumi Up` run on `main` reports `unchanged`, and both
firewalls list the app's UUID:

```bash
for c in platform-postgres platform-valkey; do
  id=$(doctl -t "$DIGITALOCEAN_TOKEN" databases list -o json | python3 -c "import json,sys;print([d['id'] for d in json.load(sys.stdin) if d['name']=='$c'][0])")
  doctl -t "$DIGITALOCEAN_TOKEN" databases firewalls list "$id" -o json | python3 -c "import json,sys;print('$c', [r['value'] for r in json.load(sys.stdin)])"
done
```

## Phase 7: verify [agent, then you]

Within a minute of onboarding the app connects on its own. No redeploy needed.

```bash
cd ~/mini/$APP
DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)" bash scripts/verify-live.sh
URL="$(pulumi -C infra stack output app_url)"
curl -s -X POST -H 'content-type: application/json' -d '{"text":"agent check","author":"agent"}' "$URL/api/notes"
curl -s "$URL/api/notes"
curl -s -o /dev/null -w '%{http_code}\n' "$URL/api/debug/error"   # 500: sends a test error to Sentry
```

**Checkpoint (agent):** `verify-live.sh` ends with `All checks passed.` and the
note comes back from `GET /api/notes`.

**[you]** finish in a browser:

1. Open the app URL and click **Sign in** under "User accounts (Clerk)". Sign
   up or in with your email and the code Clerk sends.
2. The page shows **"Backend /me says: user_id: user_…"**.
3. Under "Database (Postgres)", type a note and click **Add**. It appears in the list.
4. Sentry → project `<APP>` → Issues shows
   `RuntimeError: Intentional test error for Sentry verification`.
5. Honeycomb → `prod` → a dataset named after the app has spans for `/api/…`.

## Phase 8: CI and repeat runs [agent]

```bash
gh run list -L 3                                  # Deploy and Checks on main: success
cd infra && DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)" \
  pulumi preview --expect-no-changes && cd ..     # "5 unchanged"
copier update --trust --defaults --vcs-ref "$(grep _commit .copier-answers.yml | cut -d' ' -f2)"
git status --short                                # empty: the update is a no-op
```

**Checkpoint:** the Deploy run succeeded with `5 unchanged`, the preview passes,
and `git status` is clean. Open a small PR to see `checks.yml` run, and leave
the merge to the person.

You're done. Every merge to `main` now deploys automatically.

---

## Known problems

| Symptom | Cause | Fix |
|---|---|---|
| Deploy workflow skipped with "set the … secrets" | Phase 3 not done | Set the secrets and re-run the workflow |
| `pulumi up`: `Unable to authenticate you` / 401 | `DIGITALOCEAN_TOKEN` not set for that command | Prefix the command with `DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/app-deployer.token)"` |
| `check-config.sh`: flagsmith wrong format | Client-side key copied | Use the **Server-side** key (`ser.…`) |
| `check-config.sh`: honeycomb wrong format | Key ID (32 chars) copied | Create a new ingest key and copy the 64-char value from the dialog |
| Health stays `"database":"waiting"` after onboarding | Onboarding not done or incomplete; the `trusted_app_ids` PR not merged and then reverted by CI | Re-run `onboard-app.sh` (it's idempotent) and merge its PR |
| `verify-live.sh`: no live URL | No live deployment when `app_url` was captured | Export `DIGITALOCEAN_TOKEN` (the script then asks DO), or check the deployment in the DO console |
| After `pulumi refresh`, `up` rewrites every env var and redeploys | DO returns env vars in its own order | Run `up` once more; it settles. Avoid refreshes |
| Older app (template before #9) crashes until onboarded; `pulumi up` doesn't fix it | Plain `up` doesn't redeploy an unchanged spec | `doctl apps create-deployment "$(pulumi -C infra stack output app_id)"`, or push to `main` |
| `pulumi destroy` gets 403 on the database, user or pool | `app-deployer` has no `database:delete` | Admin runs destroy (below) |

## Teardown [admin]

Not part of setup. Run it only when someone decides to remove the app.

```bash
cd ~/mini/$APP/infra
DIGITALOCEAN_TOKEN="$(cat ~/.config/platform/do-admin.token)" pulumi destroy
pulumi stack rm prod
```

Then:
1. Open a platform-infra PR that removes the app's UUID from `trusted_app_ids`
   (after the destroy).
2. Delete the repo (`gh repo delete srainier/$APP`).
3. Delete the Clerk application, the Flagsmith server-side key, the Sentry
   project and the Honeycomb ingest key. Keep `hello_banner`.
