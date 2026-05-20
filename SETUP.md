# Reclaim Outreach Agent — Cloud Setup

This agent runs **on GitHub's servers**, not your laptop. Once set up, it
runs on its own — your laptop can be off, asleep, or sold. Nothing to open,
nothing to switch on.

## How it runs

- GitHub Actions wakes the agent **every 15 minutes, Mon–Fri**, during a
  US-morning window (12:00–18:00 UTC).
- Each wake-up ("tick") sends up to `BATCH_SIZE` emails, then stops.
- Once `DAILY_CAP` emails have gone out for the day, later ticks do nothing.
- State (who's been emailed) lives in `outreach.db`, which the agent commits
  back to the repo after every tick — so it never double-emails anyone.

## One-time setup

### 1. Create a GitHub account
Go to github.com and sign up (free) if you don't have an account.

### 2. Create a private repository
New repository → name it e.g. `reclaim-outreach` → set it to **Private**
(this keeps your leads list private) → create it empty.

### 3. Push this project to the repository
From this project folder, run the commands GitHub shows you on the new
empty-repo page. They look like:

```
git remote add origin https://github.com/YOUR-NAME/reclaim-outreach.git
git branch -M main
git push -u origin main
```

(The project is already a git repo with an initial commit — you only need
to connect it and push.)

### 4. Add your config in GitHub
In the repository: **Settings → Secrets and variables → Actions**.

**Secrets tab** — click "New repository secret":

| Name | Value |
|------|-------|
| `MAILERSEND_API_KEY` | your MailerSend API key |

**Variables tab** — click "New repository variable" for each:

| Name | Value |
|------|-------|
| `DRY_RUN` | `true` (keep it true until you've tested — see step 6) |
| `DAILY_CAP` | `30` |
| `BATCH_SIZE` | `2` |
| `SENDER_NAME` | your name |
| `SENDER_COMPANY` | `Reclaim` |
| `SENDER_EMAIL` | your sending address (on your verified MailerSend domain) |
| `REPLY_TO_EMAIL` | where replies should land (blank = same as SENDER_EMAIL) |
| `SENDER_ADDRESS` | your real postal address (legally required in the footer) |
| `UNSUBSCRIBE_URL` | your opt-out page URL |
| `APP_URL` | your web-app link — the button prospects click |

### 5. Add your leads
Save your Apollo.io export as `leads.csv` in the repo (columns:
`FirstName,LastName,CompanyName,Title,Email,LinkedInURL`), then commit and
push it. `leads.sample.csv` shows the exact format.

### 6. Test, then go live
- In the repo's **Actions** tab, select "Reclaim Outreach Agent" → **Run
  workflow**. With `DRY_RUN=true` it runs the whole pipeline but sends
  nothing — check the run log to confirm the emails look right.
- When you're happy, change the `DRY_RUN` variable to `false`. The agent is
  now live and will send on schedule.

## Day-to-day

- **Nothing.** It runs itself. Check the **Actions** tab any time to see runs.
- **Opens & clicks:** your MailerSend dashboard → Analytics.
- **Someone asks to unsubscribe:** add their email to the suppression list.
  Locally: `python suppress_email.py their@email.com`, then commit
  `outreach.db`. (We can automate this later.)
- **Adjust pace:** change the `DAILY_CAP` / `BATCH_SIZE` variables in GitHub —
  no code change, no redeploy.
