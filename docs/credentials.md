# Credentials for a new app

Step-by-step instructions for collecting the five runtime values a new app needs
(README steps 9–10). Each service shows several look-alike keys, so each section
ends with a **Copy this / Not these** table.

UI paths were checked against each vendor's docs in October 2026. If a menu has
moved, the key formats in the tables are the reliable check.

## How to store each value

Run these from the app repo root. Copy a value in the vendor UI, then
immediately run its command. `pbpaste` keeps the secret out of your shell
history and terminal output:

```bash
pbpaste | pulumi -C infra config set clerk_publishable_key
pbpaste | pulumi -C infra config set --secret clerk_secret_key
pbpaste | pulumi -C infra config set --secret flagsmith_api_key
pbpaste | pulumi -C infra config set --secret sentry_dsn
pbpaste | pulumi -C infra config set --secret honeycomb_api_key
```

Run `pulumi stack init prod` in `infra/` first. The encrypted values land in
`infra/Pulumi.prod.yaml`, which **is** committed because CI reads it.

For local development, `bash scripts/dev-env.sh` copies these same values into
the git-ignored `backend/.env` and `frontend/.env.local` without printing them.
It refuses to write to a file git would track.

## What a correct value looks like

| Config key | Format |
|---|---|
| `clerk_publishable_key` | `pk_test_…` |
| `clerk_secret_key` | `sk_test_…` |
| `flagsmith_api_key` | `ser.…` (about 26 characters) |
| `sentry_dsn` | `https://<hex>@o<digits>.ingest.us.sentry.io/<digits>` |
| `honeycomb_api_key` | `hcaik_…`, **64 characters** |

You can check them without printing the secrets:

```bash
cd infra
pulumi config get honeycomb_api_key | tr -d '\n' | wc -c   # expect 64
curl -s -H "X-Honeycomb-Team: $(pulumi config get honeycomb_api_key)" \
  https://api.honeycomb.io/1/auth                          # expect "type":"ingest"
curl -s -H "X-Environment-Key: $(pulumi config get flagsmith_api_key)" \
  https://edge.api.flagsmith.com/api/v1/flags/             # expect a list incl. hello_banner
```

---

## 1. Clerk: publishable key + secret key

1. Go to **dashboard.clerk.com**. Use the application switcher (top left) and
   choose **Create application**.
   - **Application name:** your app's display name.
   - **Sign-in options:** leave **Email** on (adding Google is fine).
     Then click **Create application**.
2. Ignore the quickstart framework picker and its code snippets.
3. Check that the instance badge next to the app name says **Development**.
4. Go to **Configure** (top tab), then **Developers → API keys** in the sidebar.
5. Copy the **Publishable key** and store it as `clerk_publishable_key`.
6. Under **Secret keys**, copy the default key and store it as
   `clerk_secret_key`.

| ✅ Copy this | ❌ Not these |
|---|---|
| `pk_test_…` (Publishable key) | `pk_live_…` / `sk_live_…`: that's the Production instance, so switch back to Development |
| `sk_test_…` (Secret key) | **JWKS URL**, **JWKS Public Key**, **Frontend API URL** (same page) |
| | "API keys" in the *machine auth* sense (keys your app issues to its users) |
| | The `NEXT_PUBLIC_…=` / `CLERK_SECRET_KEY=` prefix from snippets: copy only the value |

## 2. Flagsmith: server-side environment key + the `hello_banner` flag

> **Free plan = one project.** Flagsmith's free plan allows a single project, so
> every app shares it (for us that's **App Template Test**). Each app gets its
> own server-side key but sees the same flags. The template's demo flag
> `hello_banner` already exists there, so skip step 3: every app reads that
> one flag, and toggling it changes all of them. Give flags you add later an
> app prefix (e.g. `my_app_new_checkout`) so apps don't collide.

1. Go to **app.flagsmith.com** and open the project. On a paid plan, create a
   project named after the app instead.
2. Select the **Production** environment in the environment switcher.
3. Create the flag: **Features → Create Feature**.
   - **Name:** `hello_banner` (exact spelling, with the underscore).
   - **Enabled by default:** your choice. When it's on, the app shows the banner.
     Then click **Create Feature**.
4. Create the key: **Environment Settings** (sometimes just **Settings**), then
   the **SDK Keys** tab.
   - Under **Server-side Environment Keys**, click
     **Create Server-side Environment Key**. Name it `<app-name>-backend` and
     click **Create**.
5. Copy the key and store it as `flagsmith_api_key`.

| ✅ Copy this | ❌ Not these |
|---|---|
| Starts with **`ser.`** | The **Client-side Environment Key** at the top of the same tab: a short string with **no `ser.` prefix**. This is the #1 mix-up |
| | **Organisation Settings → API Keys** (admin keys for managing Flagsmith itself) |
| | The environment **ID** shown in URLs |

## 3. Sentry: DSN

1. Go to **sentry.io**. Click **Projects** in the sidebar, then
   **Create Project** (top right).
2. **Choose your platform:** **FastAPI** (Python, not JavaScript).
3. **Alert frequency:** leave the default.
4. **Project name:** the app name. **Team:** your default team. Then click
   **Create Project**.
5. On the setup page that follows, copy only the string inside
   `sentry_sdk.init(dsn="…")` and store it as `sentry_dsn`.
   - If you navigated away, it's under
     **Settings → Projects → \<app\> → Client Keys (DSN)**, in the field labelled
     **DSN**.

| ✅ Copy this | ❌ Not these |
|---|---|
| A full URL containing `@`, ending in digits | **Public Key** / **Secret Key** shown separately (these are fragments of the DSN) |
| | **Security Header**, **Minidump**, **Unreal**, **OTLP** endpoints (same page) |
| | **Auth Tokens** (`sntrys_…`), which are for the Sentry API, not the app |

## 4. Honeycomb: ingest key

> **US region only.** The template sends to `api.honeycomb.io`. If your
> Honeycomb UI is at `ui.eu1.honeycomb.io`, change `HONEYCOMB_ENDPOINT` in
> `backend/app/telemetry.py` to `https://api.eu1.honeycomb.io/v1/traces`.

1. Go to **ui.honeycomb.io**. Open the **environment selector** in the left nav
   and choose **Manage Environments**.
2. Pick the environment (we use **prod**).
3. Go to **API Keys**, open the **Ingest** tab, and click **Create API Key**.
   - **Name:** the app name.
   - **Can create services/datasets:** leave it **on**, so the dataset appears on
     the first trace.
4. **Copy the key from the dialog that appears right after Create.** It's shown
   **only once**. Store it as `honeycomb_api_key` before closing the dialog.

| ✅ Copy this | ❌ Not these |
|---|---|
| The **64-character** value from the creation dialog, starting `hcaik_` | The **Key ID** in the key list. It *also* starts with `hcaik_` but is only **32 characters**, and Honeycomb rejects it as `unauthenticated`. If that's all you have, create a new key |
| | Anything from the **Configuration** tab (manages boards and triggers; can't send data) |
| | **Management keys** (`hcamk_…`) under team/account settings |

---

## Not part of this list

- **`DIGITALOCEAN_TOKEN`**: the scoped `app-deployer` token. See platform-infra →
  "Granting a new app-owner". Use it locally and as the app repo's GitHub
  Actions secret.
- **`PULUMI_ACCESS_TOKEN`** (GitHub Actions secret only): create a dedicated
  token in Pulumi Cloud → **Personal access tokens**. Don't reuse your CLI
  login.
- **Setup-only tokens** for `scripts/setup-saas.sh` (`FLAGSMITH_SERVER_API_KEY`,
  `SENTRY_AUTH_TOKEN`, `HONEYCOMB_CONFIGURATION_API_KEY`): never store these in
  the repo, in Pulumi config, or in GitHub secrets.
