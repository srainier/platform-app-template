# SaaS resources are created manually or by scripts/setup-saas.sh, not Pulumi.
#
# Runtime SaaS values are stored as Pulumi config secrets so Pulumi can inject
# them into App Platform. They are not GitHub Actions secrets:
#   - clerk_secret_key: Clerk Development secret key.
#   - flagsmith_api_key: server-side Flagsmith environment key.
#   - sentry_dsn: Sentry project DSN.
#   - honeycomb_api_key: Honeycomb ingest key.
#
# See README.md -> "Post-Scaffold Setup" for the full checklist.
