# SaaS Per-App Resource Setup
#
# The following services do not have reliable Pulumi providers.
# Run scripts/setup-saas.sh to create per-app resources via their REST APIs.
# The script will print the API keys you need to add as GitHub Actions secrets.
#
# Services:
#   - Clerk: Create a new Application in the Clerk dashboard (manual step).
#             Store CLERK_SECRET_KEY as a GitHub Actions secret.
#   - Flagsmith: Created automatically by setup-saas.sh
#                Store FLAGSMITH_API_KEY as a GitHub Actions secret.
#   - Sentry: Created automatically by setup-saas.sh
#             Store SENTRY_AUTH_TOKEN + SENTRY_DSN as GitHub Actions secrets.
#   - Honeycomb: Created automatically by setup-saas.sh
#                Store HONEYCOMB_API_KEY as a GitHub Actions secret.
#
# After running setup-saas.sh:
# 1. Copy the printed keys into GitHub Actions secrets (gh secret set <NAME>)
# 2. Re-run `pulumi up` to inject the new secrets into App Platform env vars
#
# See README.md → "Post-Scaffold Setup" for the full checklist.
