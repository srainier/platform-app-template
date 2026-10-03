# Automation roadmap

What still needs a person when starting a new app, and how to remove it. This is
based on the `hello-verify` end-to-end run (October 2026); the current
procedure is [new-app-guide.md](new-app-guide.md).

## Where we are

After the fixes in PR #9 and the scripts added with the guide, an agent can do
everything from scaffolding to a verified live app. People are still needed for:

| Manual work | Per | Why it's manual today |
|---|---|---|
| Issue `app-deployer` token, add to Pulumi team | person | DO and Pulumi admin UIs |
| Pulumi CI token | person | Pulumi UI |
| DO GitHub app repo access | app (unless "All repositories") | GitHub UI |
| Clerk app + 2 keys | app | Clerk UI |
| Flagsmith server-side key | app | Flagsmith UI |
| Sentry project + DSN | app | Sentry UI |
| Honeycomb ingest key | app | Honeycomb UI |
| Onboarding + merging its PR | app | Shared-infra boundary (deliberate) |
| Browser sign-in, dashboard checks | app | Needs a human login |

## Suggestions, highest value first

### 1. Provision the SaaS keys by API (removes most of Step 0.3)
Each vendor except Clerk can create what an app needs through an API, given one
long-lived management credential that the person sets up once:

| Vendor | One-time credential | Per-app call |
|---|---|---|
| Sentry | org auth token (`project:write`) | create project under the team, read its DSN from the client-keys endpoint |
| Honeycomb | management key (`hcamk_…`) with API-key scope | create an ingest key in the `prod` environment; the response contains the full secret |
| Flagsmith | organisation API key | create a server-side environment key for the shared project's Production environment |

`scripts/setup-saas.sh` already has the start of this, but it stops at "copy
keys from the UIs". Finish it so it writes straight into Pulumi config (like
`load-config.sh`), and keep the three management credentials in
`~/.config/platform/` next to the DO token. Step 0.3 then shrinks to Clerk only.
Effort: about a day, mostly API details and idempotency (re-running must
reuse, not duplicate).

### 2. Keep SaaS values in Pulumi ESC instead of a hand-off file
A Pulumi ESC environment per app (for example `platform/<app>`) that the stack
imports would let a person paste values once into the Pulumi UI. Then no
plaintext file ever exists on disk, and an agent never handles secrets. It also
gives one place to rotate keys. Check that ESC is included in the current
Pulumi plan before adopting it. Effort: half a day in the template's
`Pulumi.yaml`/config code plus docs.

### 3. Remove per-app GitHub secrets
- Set `DIGITALOCEAN_TOKEN` and `PULUMI_ACCESS_TOKEN` once as **organisation or
  user-level** Actions secrets (if the repos move to an org), or
- replace `PULUMI_ACCESS_TOKEN` with **Pulumi OIDC for GitHub Actions** (Pulumi
  Cloud trusts the repo's workflow identity; no stored token at all).

Either way, Phase 3 disappears. Effort: an hour for org secrets; half a day for
OIDC including the workflow change.

### 4. Set the DO GitHub app to "All repositories"
One click, and the per-app repo-access step is gone. The trade-off is that
DigitalOcean can read every repo in the account.

### 5. Turn onboarding into a reviewed PR instead of a direct apply
Today `onboard-app.sh` applies production changes directly and then asks for a
PR to catch `main` up, the one exception to "prod changes go through `main`".
Alternative:

1. The app-owner (or agent) opens a platform-infra PR adding the app's UUID to
   `trusted_app_ids`. A small script can do this, because the UUID is in the app
   stack's `app_id` output.
2. The PR preview shows the firewall diff. The admin reviews and merges.
3. A platform-infra workflow on `main` runs `pulumi up` (already the case) and
   then the schema `GRANT`, using the admin token stored as a platform-infra
   secret.

The admin's whole job becomes "review and merge a PR". The direct-apply
exception and the "merge it NOW or CI locks the app out" risk both go away. The
hard part is the `GRANT` from a CI runner: it needs a temporary trusted IP, as
the script does today, or a Pulumi `postgresql` provider resource. Effort: about
a day.

### 6. One entry point: `scripts/bootstrap.sh`
Wrap Phases 1–5 and 7 in one idempotent script driven by the Step 0 hand-off
checklist. Each phase checks whether it's already done (repo exists, secrets
set, stack exists, config valid, app live) and skips or resumes. Agents then
run one command and report its output. Machine-readable output (`--json`) from
`preflight`, `check-config` and `verify-live` would make agent runs easier to
check. Effort: half a day once 1–3 are in place.

### 7. Let verification cover Sentry and Honeycomb
`verify-live.sh` can't confirm that errors and traces arrive, because the app
only holds write keys. With a Sentry read token and a Honeycomb query-capable
key in `~/.config/platform/`, the script can trigger `/debug/error` and then
poll each API for the event. That leaves the browser sign-in as the only human
check. Effort: a few hours.

### 8. Version the template
The template has no git tags, so `copier copy` and `copier update` always use
`main` HEAD. During this run, PR #8 merged a minute before scaffolding and
changed what "the template" meant mid-test. Tag releases (`v0.x`), and record
the tag in the guide's hand-off checklist so a run is reproducible.

### 9. Teardown script
`scripts/teardown.sh` with the order made explicit: destroy with the admin token
→ PR removing the UUID → delete repo → print the SaaS cleanup list (or delete
via the same APIs as suggestion 1). It should refuse without `--yes`.

## Template issues found that aren't setup problems

- `POST /api/notes` accepts anonymous writes from anyone with the URL, and the
  frontend sends the literal author `"signed-in"` rather than the user. Send the
  Clerk token and take the author from the verified user id.
- `/api/debug/error` is public in production and can flood Sentry. Gate it
  behind an environment check or auth.
- Each app's connection pool reserves 5 connections on the 1 GB Postgres node
  (about 22 usable), so roughly 4 apps fit before pool sizes need tuning or the
  node needs to grow.
