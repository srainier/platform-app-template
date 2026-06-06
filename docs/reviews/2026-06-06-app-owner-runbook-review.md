# Review: app-owner runbook branch

Scope reviewed: `platform-app-template` branch `docs/app-owner-runbook`
against `main` (`09533f0`), with background context from
`/Users/srainier/dev/side_projects/hello-platform-DEPLOY-HANDOFF.md` and the
platform role-separation design. I did not review the sibling `platform-infra`
branch except as context for the app-owner-facing contract.

Overall direction is right: the branch moves the generated app docs away from an
all-powerful operator model and introduces the required platform-admin
onboarding step. The remaining issues are mostly runbook accuracy problems that
can still derail the first scaffold/deploy.

## Ordered feedback

1. **High: the prominent deploy instructions can fail before the app stack exists.**

   The new generated README deployment section tells app owners to set Pulumi
   config first (`template/README.md.jinja:99-102`) and only then run
   `cd infra && pulumi up` (`template/README.md.jinja:103`). That sequence
   omits `cd infra` before the config commands and omits `pulumi stack init prod`
   before the first `pulumi config set`. In a freshly scaffolded repo, running
   those commands from the repo root has no Pulumi project, and running them
   before stack initialization has no selected app stack.

   The top-level README has a related executable-flow problem: it runs `cd infra`
   at `README.md:70`, then later runs `cd infra && pulumi stack init prod &&
   pulumi up` at `README.md:77`, which resolves to `infra/infra` if followed as
   one shell transcript. Since this branch turns the surrounding section into the
   app-owner runbook, it is worth fixing the command flow now.

   Recommendation: make the first deploy sequence single-path and copy/pasteable:
   `cd infra`, `pulumi stack init prod`, set all config, then `pulumi up`.
   Avoid a second `cd infra` once already inside the directory.

2. **High: frontend-enabled apps are still missing the required Clerk publishable-key step in two runbooks.**

   The template requires `clerk_publishable_key` when `include_frontend` is true
   (`template/infra/resources/config.py.jinja:15-20`) and injects it into the
   static-site build environment (`template/infra/resources/app_platform.py.jinja:67-75`).
   The new generated deployment section mentions this once
   (`template/README.md.jinja:101-102`), but the top-level Usage flow only sets
   `clerk_secret_key`, `flagsmith_api_key`, `sentry_dsn`, and
   `honeycomb_api_key` (`README.md:69-74`). The generated README's
   "Post-Scaffold Setup" repeats the same omission (`template/README.md.jinja:153-160`),
   and `scripts/setup-saas.sh` prints the same incomplete final command list
   (`template/scripts/setup-saas.sh.jinja:100-108`).

   Result: a frontend app owner can follow either the top-level README or the
   post-scaffold section exactly and still have `pulumi up` fail with a missing
   required config key.

   Recommendation: include the publishable-key command everywhere the required
   Pulumi config commands are listed, guarded with the same frontend-only wording
   used in `Pulumi.prod.yaml.jinja`.

3. **Medium: the top-level Pulumi prerequisite overstates what the platform admin grants.**

   The app-owner model is that the app owner creates their own app stack and has
   admin rights there, while the platform admin grants Read on
   `platform-infra/prod`. The top-level README instead says to ask the platform
   admin to grant Pulumi **Admin** on the app stack and **Read** on
   `platform-infra/prod` (`README.md:25-27`). That is awkward before the app stack
   exists and muddies the role boundary the branch is trying to clarify.

   Recommendation: align this with the generated README wording: the admin grants
   Pulumi access to platform outputs; the app owner initializes/owns the app
   stack.

4. **Medium: SaaS credential ownership is still inconsistent with the new role model.**

   The new generated README says app owners use `scripts/setup-saas.sh` output to
   set Pulumi config (`template/README.md.jinja:99-102`) and the credentials
   table lists only runtime values like `sentry_dsn` and `honeycomb_api_key`
   (`template/README.md.jinja:117-128`). But the setup script still asks for
   "admin" SaaS API keys (`template/scripts/setup-saas.sh.jinja:10-15`) and tells
   users to add values like `SENTRY_AUTH_TOKEN` and `HONEYCOMB_API_KEY` to GitHub
   secrets (`template/scripts/setup-saas.sh.jinja:57-63`,
   `template/scripts/setup-saas.sh.jinja:81-83`,
   `template/scripts/setup-saas.sh.jinja:112-113`). The deploy workflow only uses
   `PULUMI_ACCESS_TOKEN` and `DIGITALOCEAN_TOKEN`, while runtime SaaS values are
   Pulumi config secrets.

   Recommendation: separate "temporary setup API tokens" from "runtime app
   secrets" in the generated docs and setup script output. If app owners are
   expected to hold Flagsmith/Sentry/Honeycomb admin-ish setup tokens, say that
   explicitly; otherwise point to manual per-app setup by someone with those SaaS
   permissions. Do not tell users to put unused setup tokens in GitHub Actions
   secrets.

5. **Medium: historical docs now have a warning, but still contain executable stale examples.**

   Adding a dated note to the old plan docs is a good compromise, but those files
   still include copyable examples that use the old platform contract:
   `postgres_host`, `postgres_admin_password`, and `redis_url` from the platform
   stack (`docs/plans/2026-04-13_platform-app-template-phase2-implementation.md:234-239`;
   `docs/plans/2026-04-13_platform-infra-brief.md:400-404`). The note at the top
   says the role model changed, but it does not warn readers not to copy the
   snippets below.

   Recommendation: either strengthen the top note to say the examples are
   historical and not safe to copy, or replace the specific stale snippets with a
   pointer to the current README while preserving the rest of the historical plan.

6. **Low: verification instructions do not tell the app owner where to get the app URL.**

   The generated README ends the first deploy flow with
   `curl https://<app-url>/api/` (`template/README.md.jinja:112`), but the app
   URL is only exported from Pulumi (`template/infra/resources/outputs.py.jinja:5`)
   and the docs do not mention `pulumi stack output app_url`. This is small, but
   it is exactly the kind of missing bridge that slows down first-time app owners.

   Recommendation: add `pulumi stack output app_url` to the verification step.

## Verification performed

- Reviewed `git diff main...HEAD` for this repo only.
- Cross-checked the changed README text against the existing template infra,
  workflow, and setup script files.
- Did not render a fresh Copier output or run the generated app workflows; this
  review is limited to static docs/runbook consistency.
