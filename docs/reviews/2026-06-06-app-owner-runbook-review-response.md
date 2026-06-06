# Response: app-owner runbook review

Responding to `docs/reviews/2026-06-06-app-owner-runbook-review.md`. Each item
below is marked **Addressed** or **Declined** with the specific change made.

Verification: re-rendered the template with `copier copy --vcs-ref=HEAD` for both
`include_frontend=true` and `include_frontend=false`; both render cleanly and the
generated `setup-saas.sh` passes `bash -n` in both variants.

---

## 1. High — deploy instructions can fail before the app stack exists. **Addressed**

Both runbooks are now single-path and copy/pasteable, with `pulumi stack init prod`
before any `pulumi config set` and exactly one `cd infra`.

- **Generated README** (`template/README.md.jinja`, "Deploying to the shared
  platform"): the first deploy is now one fenced block — `cd infra` →
  `pulumi stack init prod` → config sets → `pulumi up` — instead of separate
  config-then-`cd infra && pulumi up` steps. No second `cd infra`.
- **Top-level README** (`README.md`, Usage steps 8–9): merged stack init into
  step 8 before the config sets, and step 9 is now a bare `pulumi up` (already
  inside `infra/` from step 8). The previous `cd infra` … then `cd infra &&
  pulumi stack init prod && pulumi up` double-`cd` (which resolved to
  `infra/infra`) and the config-before-init ordering bug are both gone.

## 2. High — frontend apps missing the Clerk publishable-key step in two runbooks. **Addressed**

The publishable-key command is now present everywhere the required Pulumi config
commands are listed, guarded by `{% if include_frontend %}` (matching
`Pulumi.prod.yaml.jinja`), so it appears only for frontend apps:

- Generated README "Deploying to the shared platform" (already had it; kept).
- Generated README "Post-Scaffold Setup" step 3 config block — **added**.
- `scripts/setup-saas.sh.jinja` final summary block — **added**.
- Top-level README Usage step 8 — **added** (unconditional with an inline
  "if you included the frontend" note, since the top-level README is the template
  repo's own docs and is not Jinja-rendered per-app).

Confirmed via render: the line appears in the `frontend=true` output and is
absent from `frontend=false`.

## 3. Medium — top-level Pulumi prerequisite overstates what the admin grants. **Addressed**

`README.md` Prerequisites now matches the spec's persona model
(`...role-separation-design.md`, Personas table): the admin adds the app owner to
the `app-owners` team granting **Read** on `platform-infra/prod` (for the
`StackReference`); the app owner creates/owns their app stack and gets **Admin**
on it automatically via `pulumi stack init`. The prior "ask the admin to grant
you Admin on your app stack" wording is removed.

## 4. Medium — SaaS credential ownership inconsistent with the role model. **Addressed**

`scripts/setup-saas.sh.jinja` now separates temporary setup tokens from runtime
app secrets:

- New header paragraph states the `*_SERVER_API_KEY` / `SENTRY_AUTH_TOKEN` /
  `HONEYCOMB_API_KEY` inputs are the owner's **personal SaaS-account setup
  tokens**, used only locally while the script runs, and must **not** go in the
  repo or GitHub Actions secrets (the deploy workflow never uses them).
- Every inline "add … to GitHub secrets" instruction (Flagsmith, Sentry,
  Honeycomb — both the success and skip/fallback branches) now says to store the
  runtime value as the corresponding **Pulumi config secret**
  (`flagsmith_api_key` / `sentry_dsn` / `honeycomb_api_key`).
- The closing note now reads: `PULUMI_ACCESS_TOKEN` and `DIGITALOCEAN_TOKEN` are
  the only values that go in GitHub Actions secrets; the SaaS setup tokens are
  local-only and belong in neither GitHub nor Pulumi.

This assumes the app owner holds their own SaaS setup tokens, which is the model
in the deploy handoff (the owner ran `setup-saas` with their own keys). The
choice is now stated explicitly rather than implied.

## 5. Medium — historical docs still contain executable stale examples. **Addressed**

Strengthened the top dated note in both historical plan docs
(`docs/plans/2026-04-13_platform-app-template-phase2-implementation.md` and
`docs/plans/2026-04-13_platform-infra-brief.md`) with an explicit
**"Do not copy the code or commands below — they are historical"** warning that
names the specific stale references (`postgres_admin_password` output, private
`postgres_host` / `redis_url`) and points readers to the current generated app
README and platform-infra README.

Chose to strengthen the note rather than rewrite the snippets, preserving the
historical plan intact (the spec's "Open questions" left this per-file decision
to impl, and these are historical planning docs).

## 6. Low — verification step doesn't say where to get the app URL. **Addressed**

The generated README's final verify step now runs
`pulumi stack output app_url` (the `app_url` export from `outputs.py.jinja`) and
pipes it into the curl: `curl "$(pulumi stack output app_url)/api/"`, bridging
the gap between the Pulumi output and the placeholder `<app-url>`.

## Follow-up — top-level README double-cd on post-onboarding redeploy. **Addressed**

`README.md` Usage step 11 still ran `cd infra && pulumi up`, which (read as one
transcript continuing from step 8's `cd infra`) resolved to `infra/infra` and
failed. Changed to a bare `pulumi up` with a `# still inside infra/ from step 8`
note, matching the fix applied to step 9.

---

## Not changed (and why)

- **`outputs.py.jinja`, `app_platform.py.jinja`, `config.py.jinja`,
  `Pulumi.prod.yaml.jinja`** — referenced only as evidence; the required-config
  and output contracts they define were already correct. The fixes were all in
  the runbook/docs/setup-script text that was inconsistent with them.
