# speech-to-sheets

Log expenses into a Google Sheet by sending a text, a voice note or a photo of a receipt to a Slack bot.

```
You:  lunch at the market 12.50
Bot:  Logged in row 236: 26/10/2026 | $12.50 | Food | Market
```

If something is missing, the bot asks in the message's thread, and your answer completes the same expense:

```
You:  taxi to the airport
Bot:  How much was it?
You:  32
Bot:  Logged in row 237: 26/10/2026 | $32.00 | Transport | Taxi to the airport
```

## Contents

- [How it works](#how-it-works)
- [What you need](#what-you-need)
- [Quick start](#quick-start)
- [Google Sheets setup](#google-sheets-setup)
- [Slack setup](#slack-setup)
- [Using it](#using-it)
- [Run it as a service on macOS](#run-it-as-a-service-on-macos)
- [Sleep and missed messages](#sleep-and-missed-messages)
- [Run it on a Linux server](#run-it-on-a-linux-server)
- [Privacy](#privacy)
- [Costs](#costs)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Design decisions](#design-decisions)
- [Development](#development)

## How it works

1. You write to the bot in a Slack direct message. It uses Slack's **Socket Mode**: the bot opens the connection to Slack, so your computer needs no public address and no open port.
2. Voice notes are transcribed **on your computer** with [whisper.cpp](https://github.com/ggml-org/whisper.cpp). Audio never leaves your machine.
3. Claude (Anthropic API, `claude-haiku-5-5`) reads the text, the transcript or the photo and returns four values: the **date** the expense happened (from the message or receipt, otherwise the day it was sent), the **amount**, a **category** from your sheet's own dropdown, and a short **description**. When unsure, it asks instead of guessing.
4. The bot writes those four cells in the next empty row of your sheet, reads the row back and replies with what the sheet now shows, so a misheard amount is easy to spot.

Your sheet keeps its own layout. The bot finds the four columns by their header text (any language), takes the categories from the category column's dropdown, and learns your naming habits from your last 30 rows. It never touches other columns.

A small local database remembers which Slack messages were handled, so a repeated or late message never adds a second row. Messages sent while the bot was stopped or the computer slept are picked up when it runs again (see [Sleep and missed messages](#sleep-and-missed-messages)).

## What you need

- **macOS or Linux.** Windows may work but is untested.
- A **Slack workspace** where you can install an app (any free workspace works).
- A **Google account** and a sheet with a header row naming a date, amount, category (a dropdown) and description column.
- An **Anthropic API key** from the [Anthropic Console](https://console.anthropic.com/). This is billed separately from Claude subscriptions; see [Costs](#costs).
- [uv](https://docs.astral.sh/uv/), whisper.cpp's `whisper-cli`, `ffmpeg`, and a whisper model file (about 575 MB).

## Quick start

1. **Get the code and the tools.**

   ```sh
   git clone https://github.com/krsmauro/speech-to-sheets.git
   cd speech-to-sheets
   brew install uv whisper-cpp ffmpeg   # macOS; for Linux see "Run it on a Linux server"
   uv sync
   ```

2. **Download the whisper model** (or another [ggml model](https://huggingface.co/ggerganov/whisper.cpp); smaller ones are faster but make more mistakes):

   ```sh
   mkdir -p models
   curl -L -o models/ggml-large-v3-turbo-q5_0.bin \
     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
   ```

3. **Create the secrets file:** `cp .env.example .env`. Then fill it in while you follow:
   - [Google Sheets setup](#google-sheets-setup): a service account, its key file, and sharing your sheet with it (about 10 minutes);
   - [Slack setup](#slack-setup): the Slack app and its two tokens (about 5 minutes);
   - your Anthropic API key. Set a monthly spend limit in the Console while you are there.

4. **Create `config.yaml`** by answering a few questions. It reads your sheet, proposes which column is which, and lets you confirm:

   ```sh
   uv run speech-to-sheets init
   ```

5. **Start the bot:**

   ```sh
   uv run speech-to-sheets run
   ```

   It checks everything first (whisper and ffmpeg, the sheet's headers and categories, the Anthropic key and model, Slack) and stops with a message naming what to fix. Then send it an expense from Slack, on your phone or computer. Stop it with Ctrl-C.

To keep it running without a terminal, see [Run it as a service on macOS](#run-it-as-a-service-on-macos) or [Run it on a Linux server](#run-it-on-a-linux-server).

## Google Sheets setup

The bot writes to your sheet through a Google **service account**: a robot Google identity with its own email address. You share the sheet with that address, the same way you would share it with a person. The bot can open only the sheets shared with it, nothing else in your Google Drive.

It takes about 10 minutes. Standard use of the Google Sheets API is free, and the bot makes about seven requests per expense, far under Google's limit of 60 reads and 60 writes per minute.

### 1. Create a Google Cloud project

1. Open the [Google Cloud console](https://console.cloud.google.com/) and sign in.
2. In the project picker at the top, choose **New project**, name it (for example `speech-to-sheets`) and create it.
3. Make sure the new project is selected in the picker before you continue.

### 2. Enable the Google Sheets API

**APIs & Services > Library**, search for **Google Sheets API**, open it and click **Enable**. The Google Drive API is not needed: the bot opens the sheet by its ID and asks only for Sheets access.

### 3. Create the service account

1. **IAM & Admin > Service accounts > Create service account**.
2. Name it (for example `speech-to-sheets`) and continue.
3. Skip the optional steps that grant roles or access. The account needs no project roles; its only access is the sheet you share with it.
4. Click **Done**.

### 4. Create a JSON key

1. On the **Service accounts** page, click the new account's email address.
2. Open the **Keys** tab, then **Add key > Create new key**.
3. Choose **JSON** and click **Create**. The browser downloads the key file. It can be downloaded only once; if you lose it, create a new key.

If Google says key creation is blocked by an organization policy (`iam.disableServiceAccountKeyCreation`): Google enforces this by default in organizations created on or after 3 May 2024, which is common with Google Workspace accounts. Either create the project with a personal Google account, or ask your Workspace admin to allow keys for this one project.

### 5. Store the key safely

The key file works like a password: anyone who has it can edit every sheet shared with the service account. Keep it outside the project folder and readable only by you:

```sh
mkdir -p ~/.config/speech-to-sheets
mv ~/Downloads/<downloaded-key>.json ~/.config/speech-to-sheets/google-key.json
chmod 600 ~/.config/speech-to-sheets/google-key.json
```

Then set its path in `.env`:

```sh
GOOGLE_SERVICE_ACCOUNT_FILE=~/.config/speech-to-sheets/google-key.json
```

If the key ever leaks, delete it in the **Keys** tab and create a new one.

### 6. Share the sheet with the service account

1. Find the service account's email: it is the `client_email` value in the key file, and it is also listed on the **Service accounts** page. It ends in `.iam.gserviceaccount.com`.
2. While you set things up, work on a copy of your sheet (**File > Make a copy**) so a mistake cannot touch your real data.
3. In the sheet, click **Share**, paste the email, choose **Editor**, untick **Notify people**, and share.

### 7. Point config.yaml at the sheet

The easy way is `uv run speech-to-sheets init`. It asks for the sheet's URL, lets you pick the tab, proposes which column holds the date, amount, category and description (guessed from what the cells hold, so any header language works; you confirm or correct it), reads the category dropdown, and asks for your timezone, the Slack member IDs of everyone who may use the bot, the whisper model file and the voice note language. It needs only `GOOGLE_SERVICE_ACCOUNT_FILE` from `.env`, writes nothing until the last question, and asks before replacing an existing `config.yaml`.

To write it by hand instead, copy `config.example.yaml` to `config.yaml` and set, under `sheets`:

- `sheet_id`: the long ID in the sheet's URL, `https://docs.google.com/spreadsheets/d/<sheet_id>/edit`.
- `tab`: the name of the tab at the bottom of the sheet.
- `columns`: the exact header text in row 1 for the date, amount, category and description columns. Case and surrounding spaces do not matter. Other columns are ignored and never written.
- `fallback_categories`: leave empty if the category column has a dropdown; the bot reads the options from it. List your categories here only if the check below says the dropdown is not readable.

### 8. Check the connection

```sh
uv run python scripts/try_sheets.py           # only reads: columns, dropdown categories, last rows
uv run python scripts/try_sheets.py --append  # also writes one test row and reads it back
```

The test row has today's date, amount 1234, the first category and the description `speech-to-sheets test row, delete me`. In the sheet, check that the date shows in your sheet's date format with the day and month the right way round, the amount is a number in your sheet's format, the category shows as a dropdown option rather than plain text, and nothing else changed. Then delete the test row.

## Slack setup

You talk to the bot in a Slack direct message. It runs as a Slack app that you create in your own workspace from `slack-app-manifest.yaml`. It takes about 5 minutes. You need permission to install apps in the workspace; in a free workspace you have it, in a company workspace an admin may have to approve the app.

### 1. Create the app from the manifest

1. Open [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**, then **From a manifest**.
2. Pick your workspace and continue.
3. Choose the **YAML** tab, replace its content with the content of `slack-app-manifest.yaml`, and continue.
4. Check the summary (four bot scopes: `im:history`, `im:read`, `files:read`, `chat:write`; one event: `message.im`; Socket Mode on) and click **Create**.

You can rename the app first by changing `name` and `display_name` in the manifest.

### 2. Install it and copy the bot token

1. In the app's settings, open **Install App** (or **OAuth & Permissions**) and click **Install to Workspace**, then **Allow**.
2. Copy the **Bot User OAuth Token**. It starts with `xoxb-`. Put it in `.env` as `SLACK_BOT_TOKEN=xoxb-...`.

### 3. Create the app-level token for Socket Mode

The manifest turns Socket Mode on, but Slack does not create this token for you.

1. Open **Basic Information** and scroll to **App-Level Tokens**.
2. Click **Generate Token and Scopes**, name it (for example `socket`), click **Add Scope**, choose `connections:write`, and click **Generate**.
3. Copy the token. It starts with `xapp-`. Put it in `.env` as `SLACK_APP_TOKEN=xapp-...`.

Both tokens are passwords for the bot. If one leaks, regenerate it in the same place (**OAuth & Permissions** for the bot token, **App-Level Tokens** for the other).

### 4. Choose who may use it

The bot ignores everyone who is not on its list, so nobody else in the workspace can write to your sheet. A household that shares one sheet lists each person.

1. In Slack, open the person's profile: for yourself, click your profile picture, then **Profile**; for someone else, click their name.
2. Click the three dots (**More**) and **Copy member ID**. It starts with `U`.
3. List every ID in `config.yaml` (`init` asks for them):

```yaml
slack:
  allowed_user_ids: [U0123ABCD, U0456EFGH]
```

To add someone later, add their ID and restart the bot. If a person writes to the bot before they are on the list, the log shows `Ignored a direct message from Slack user U...` with their ID.

### 5. Check the connection

```sh
uv run python scripts/try_slack.py
```

In Slack, find the app under **Apps** in the sidebar (or search for its name) and open its **Messages** tab. Each person on the list does this in their own Slack and gets their own conversation with the bot. Send it a short text, a voice clip (the microphone button), a photo of a receipt, and a reply in the thread of one of its answers. It answers each one with what it received: the text length, each file's type and size, whether a photo can be sent to Claude, and the transcript of a voice clip. Nothing is written to the sheet. Stop the script with Ctrl-C.

If the Messages tab says that sending messages to this app is turned off, open **App Home** in the app's settings, make sure **Messages Tab** is on and **Allow users to send Slash commands and messages from the messages tab** is ticked, then restart Slack.

### Updating an existing app

An app created from an older manifest lacks the `im:read` scope, and the bot stops at startup with `missing_scope: add im:read`. To add it:

1. Open [api.slack.com/apps](https://api.slack.com/apps) and pick the app.
2. Open **App Manifest**, replace its content with the current `slack-app-manifest.yaml`, and click **Save Changes**. (Or open **OAuth & Permissions** and add `im:read` under **Bot Token Scopes**.)
3. Slack shows a banner asking to reinstall the app. Click **reinstall your app**, then **Allow**.
4. On **OAuth & Permissions**, check that the **Bot User OAuth Token** still matches `SLACK_BOT_TOKEN` in `.env`. Then start the bot again.

## Using it

- Send one expense per message, as text, a voice note or a receipt photo. A message with two expenses gets a question.
- Answer the bot's questions **in the thread** (tap the reply under the question). A new message counts as a new expense.
- A reply in a thread that is already logged (a "thanks", say) logs nothing.
- Dates: "yesterday", "last Friday" or a date on a receipt are understood. A date in the future gets a question, and Claude asks you to confirm a date more than 60 days back.
- Amounts can be in any currency with or without cents. They are written as plain numbers; the sheet's own format shows them. Nothing is converted between currencies.
- The bot's questions follow your language. The few fixed replies (the confirmation, errors) are in English.
- To fix or delete an entry, edit the sheet. The bot never changes a row after writing it.
- If something fails, the reply says what. Replying in that thread tries again.

## Run it as a service on macOS

Run only **one copy** of the bot per Slack app. Slack splits the messages between all connected copies, so a copy in a terminal next to the service would each see only some messages. Stop the service before running the bot in a terminal.

The service is a launchd agent: it starts when you log in and starts again if it stops. It runs a copy of the code, made by the install command, so editing your checkout changes nothing until you install again. It reads everything from one folder, `~/.config/speech-to-sheets` (set `SPEECH_TO_SHEETS_HOME` to use another):

| File | What it is |
|---|---|
| `config.yaml` | Your settings. Relative paths in it start from this folder. |
| `.env` | Your secrets. |
| `google-key.json` | The Google key (point `GOOGLE_SERVICE_ACCOUNT_FILE` at it). |
| `models/` | The whisper model; set `stt.model_path: models/<file>.bin`. |
| `dedupe.sqlite` | Created by the bot: the messages it already handled. |

Put those files there, then:

```sh
deploy/macos/service.sh install   # install or update, then start; waits for the startup checks
deploy/macos/service.sh status    # running or not, and the last log lines
deploy/macos/service.sh logs      # follow the log (~/Library/Logs/speech-to-sheets/bot.log)
deploy/macos/service.sh stop      # stop until the next login or start
deploy/macos/service.sh start
deploy/macos/service.sh restart   # after editing config.yaml or .env
deploy/macos/service.sh uninstall # remove the service; your folder is kept
```

If a startup check fails, `install` and `start` show the message and stop the service, so it does not retry every minute. Fix the problem and run `start`. A failure at login, such as no network yet, is retried every minute on its own.

To update: `git pull`, then `deploy/macos/service.sh install`.

## Sleep and missed messages

A sleeping computer cannot answer. Nothing is lost, though: at startup and every 5 minutes, the bot looks through its direct messages for ones it never handled and answers them, dated the day they were sent. After a Mac wakes, missed messages are answered within about 5 minutes. The very first start only notes the time, so messages sent before the bot ever ran are skipped. It looks back at most `dedupe.retention_days` (30 by default).

On a MacBook you can keep the bot answering while you are out, on battery:

```sh
deploy/macos/away.sh 6     # stay awake for 6 hours (default 8), display off
deploy/macos/away.sh stop  # back home: sleep normally again
```

Away mode keeps the Mac from sleeping but lets the display turn off. **Leave the lid open**: closing it puts the Mac to sleep anyway. Low Power Mode (System Settings > Battery) saves more battery, though voice notes may take longer to transcribe. How long the battery lasts depends on your Mac; check the level after your first outing.

A cheap always-on server avoids the problem altogether.

## Run it on a Linux server

A server answers even when your laptop is closed. You can bring the `config.yaml` you made on your computer, or create it on the server. There are two ways to run it:

- **Path A: Docker Compose.** One command builds everything, including `whisper-cli`. Easiest to update and to remove.
- **Path B: systemd without Docker.** You install the tools yourself. Uses a little less disk and memory.

The commands are for Debian and Ubuntu. Other distributions work too, with their own package names. As on macOS, run only one copy of the bot per Slack app: stop the copy on your laptop before you start the server. If the bot ran somewhere else before, copy that `dedupe.sqlite` into the server's data folder; it remembers which messages were already handled.

### Choosing a server

These are estimates, not measured on a server.

- **With voice notes:** 2 vCPU, 4 GB RAM and 20 GB disk. The default model file is about 575 MB, and whisper.cpp needs roughly 1 to 1.5 GB of RAM while it transcribes. 2 GB of RAM plus swap may work.
- **Speed:** without a GPU, transcription is much slower than on an Apple Silicon Mac. A short voice note can take tens of seconds on 2 vCPUs. If transcriptions time out, raise `stt.timeout_seconds` in `config.yaml`.
- **Smaller models** such as `ggml-small.bin` or `ggml-base.bin` (same download folder as the default model) are faster and use less memory, but make more mistakes.
- **Text and photos only:** the bot is idle most of the time and 512 MB to 1 GB of RAM is enough. It still checks for `whisper-cli`, `ffmpeg` and a model file when it starts, so install them anyway; a small model keeps the download small.
- x86 and ARM servers both work. The bot needs no inbound port and no public address: it only opens outgoing HTTPS connections to Slack, Anthropic and Google.

### The data folder

The bot runs inside one data folder, its working directory, holding `config.yaml`, `google-key.json`, `models/ggml-large-v3-turbo-q5_0.bin`, the `dedupe.sqlite` it writes, and with path A also `.env` (path B keeps the secrets in `/etc/speech-to-sheets/env`). On the server, `config.yaml` should say:

```yaml
stt:
  whisper_cli: whisper-cli
  ffmpeg: ffmpeg
  model_path: models/ggml-large-v3-turbo-q5_0.bin
```

`whisper-cli` and `ffmpeg` are the defaults, so you can also leave those two lines out. If you copy a `config.yaml` from a Mac, replace any Mac paths such as `/opt/homebrew/bin/whisper-cli`. The secrets are the four variables from `.env.example`; `GOOGLE_SERVICE_ACCOUNT_FILE` must be the key's path as the bot sees it, which differs between the two paths.

### Path A: Docker Compose

1. **Install Docker** Engine and the Compose plugin by following [the Docker docs for your distribution](https://docs.docker.com/engine/install/). If your user is not in the `docker` group, put `sudo` in front of each `docker` command. Then get the code; run the `docker compose` commands below from `deploy/docker`:

   ```sh
   git clone https://github.com/krsmauro/speech-to-sheets.git
   cd speech-to-sheets/deploy/docker
   ```

2. **Build the image** with `docker compose build`. This compiles `whisper-cli` and takes a few minutes. Build on the server that runs the bot: the build tunes `whisper-cli` for that CPU, and the result may crash on another CPU. To build a portable image instead, add `args: {GGML_NATIVE: "OFF"}` under `build:` in `compose.yaml`; it runs slower.

3. **Fill the data folder**, `/srv/speech-to-sheets`. Inside the container it is `/data`, and the bot runs as user ID 10001, so that user must own it.

   ```sh
   sudo install -d -m 700 /srv/speech-to-sheets /srv/speech-to-sheets/models
   sudo curl -L -o /srv/speech-to-sheets/models/ggml-large-v3-turbo-q5_0.bin \
     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
   sudo mv ~/google-key.json /srv/speech-to-sheets/google-key.json   # after copying it over with scp
   sudo nano /srv/speech-to-sheets/.env
   ```

   In `.env`, the key path is the one inside the container:

   ```sh
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ANTHROPIC_API_KEY=...
   GOOGLE_SERVICE_ACCOUNT_FILE=/data/google-key.json
   ```

   Then hand the folder to the bot's user and lock the secrets:

   ```sh
   sudo chown -R 10001:10001 /srv/speech-to-sheets
   sudo chmod 600 /srv/speech-to-sheets/.env /srv/speech-to-sheets/google-key.json
   ```

   Last, `config.yaml`: copy yours in the same way (then run the `chown` command again), or create it on the server with `docker compose run --rm bot speech-to-sheets init`. To use another folder, put `SPEECH_TO_SHEETS_DATA=/your/folder` in front of each `docker compose` command.

4. **Start it** with `docker compose up -d`, and watch it with `docker compose logs -f`. The container restarts by itself after a crash or a reboot. Logs are rotated (3 files of 10 MB). Stop it with `docker compose down`.

To update: `git pull`, then `docker compose up -d --build`. Once a month, rebuild from fresh base images to get security fixes for Debian, Python and ffmpeg inside the image: `docker compose build --pull --no-cache`, then `docker compose up -d`.

### Path B: systemd without Docker

The bot runs as its own system user, `speech-to-sheets`. The app lives in `/opt/speech-to-sheets`, the data folder is `/var/lib/speech-to-sheets`, and the secrets are in `/etc/speech-to-sheets/env`.

1. **Install ffmpeg and build whisper-cli:**

   ```sh
   sudo apt update
   sudo apt install -y ffmpeg git curl ca-certificates build-essential cmake
   git clone --depth 1 --branch v1.9.5 https://github.com/ggml-org/whisper.cpp.git
   cmake -S whisper.cpp -B whisper.cpp/build -DBUILD_SHARED_LIBS=OFF \
     -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF
   cmake --build whisper.cpp/build --target whisper-cli -j "$(nproc)"
   sudo install -m 755 whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli
   ```

2. **Install uv and the app.** uv installs the exact dependency versions in `uv.lock`, and a Python 3.12 of its own under `/opt`. Python must live under `/opt`, not in a home folder: the service cannot see `/home` or `/root`.

   ```sh
   curl -LsSf https://astral.sh/uv/0.13.1/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
   git clone https://github.com/krsmauro/speech-to-sheets.git
   cd speech-to-sheets
   sudo env UV_PYTHON_INSTALL_DIR=/opt/speech-to-sheets/python \
     UV_PROJECT_ENVIRONMENT=/opt/speech-to-sheets/venv \
     uv sync --locked --no-dev --no-editable --compile-bytecode --managed-python
   ```

3. **Create the user, the data folder and the secrets:**

   ```sh
   sudo useradd --system --home-dir /var/lib/speech-to-sheets --shell /usr/sbin/nologin speech-to-sheets
   sudo install -d -m 700 -o speech-to-sheets -g speech-to-sheets \
     /var/lib/speech-to-sheets /var/lib/speech-to-sheets/models
   sudo -u speech-to-sheets curl -L -o /var/lib/speech-to-sheets/models/ggml-large-v3-turbo-q5_0.bin \
     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin
   sudo install -m 600 -o speech-to-sheets -g speech-to-sheets ~/google-key.json /var/lib/speech-to-sheets/
   rm ~/google-key.json
   sudo install -d -m 700 /etc/speech-to-sheets
   sudo install -m 600 /dev/null /etc/speech-to-sheets/env
   sudo nano /etc/speech-to-sheets/env
   ```

   Only root can read the secrets file; systemd passes the values to the bot:

   ```sh
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ANTHROPIC_API_KEY=...
   GOOGLE_SERVICE_ACCOUNT_FILE=/var/lib/speech-to-sheets/google-key.json
   ```

   Last, `config.yaml`: copy yours in with `sudo install -m 600 -o speech-to-sheets -g speech-to-sheets ~/config.yaml /var/lib/speech-to-sheets/`, or create it on the server:

   ```sh
   sudo -u speech-to-sheets sh -c 'cd /var/lib/speech-to-sheets &&
     GOOGLE_SERVICE_ACCOUNT_FILE=google-key.json /opt/speech-to-sheets/venv/bin/speech-to-sheets init'
   ```

4. **Start it**, from the `speech-to-sheets` folder:

   ```sh
   sudo install -m 644 deploy/linux/speech-to-sheets.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now speech-to-sheets
   journalctl -u speech-to-sheets -f
   ```

   The service starts at boot and restarts after a crash. If a startup check fails, for example because the network is not up yet, it tries again every minute.

To update, from the `speech-to-sheets` folder: `git pull`, run the `uv sync` command from step 2 again, then the `install` and `daemon-reload` lines from step 4, then `sudo systemctl restart speech-to-sheets`.

### Check that it works

In the logs, a good start ends with `⚡️ Bolt app is running!`. Then send the bot a direct message in Slack and watch the reply. If a check fails, the log has a line starting with `Not started:` that says what to fix. Fix it; the bot retries by itself (path A within about a minute, path B every minute), or restart it right away.

### Hardening

- **Firewall.** The bot needs no inbound port, so block everything except SSH:

  ```sh
  sudo apt install -y ufw
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow OpenSSH
  sudo ufw enable
  ```

  Docker opens published container ports even past ufw. `compose.yaml` publishes none; keep it that way.
- **SSH.** Log in with SSH keys and turn off password login.
- **Not root.** Both paths run the bot as an unprivileged user. The systemd unit also blocks writes outside the data folder, hides home folders and limits system calls; the Compose file makes the container read-only except `/data` and `/tmp`, drops all Linux capabilities and blocks privilege escalation.
- **Secrets.** Keep the Google key and the secrets file at mode 600. Anyone with the key can edit every sheet shared with the service account. If a secret leaks, revoke it: create a new Slack token, Anthropic key or Google key and delete the old one.
- **Security updates.** Turn on automatic updates with `sudo apt install -y unattended-upgrades` and `sudo dpkg-reconfigure -plow unattended-upgrades`. With Docker, also rebuild the image once a month (see path A); the server's updates do not reach inside the image.

## Privacy

| Where | What |
|---|---|
| **Anthropic** (Claude API) | The text of the thread, including the bot's own questions; voice note **transcripts**; receipt **photos**; your category list; and your last 30 sheet rows (date, amount, category, description) as examples. Set `extract.example_rows` lower to send fewer. See [Anthropic's privacy policy](https://www.anthropic.com/legal/privacy). |
| **Your computer** | Voice notes are downloaded and transcribed in a temporary folder that is deleted right after. `dedupe.sqlite` holds Slack message IDs, row numbers and times, never what anyone wrote. The log holds message IDs, row numbers and errors, never message text. |
| **Google** | The four cells of each new row, in your sheet. The bot reads row 1, the category dropdown and the last rows on every message. The service account can open only the sheets you share with it. |
| **Slack** | Your messages and the bot's replies, as in any Slack conversation. The bot sees only direct messages sent to it and their files, never channels or other conversations. To catch up on missed messages it lists its own direct message conversations (`im:read`) and reads only the ones with people on its list. |

## Costs

- **Anthropic:** pay as you go. In this project's tests, 26 text messages cost under one cent in total. Photos cost more because the image is sent too. Set a monthly limit in the Console.
- **Google Sheets API** and **Slack** (free plan): free at this volume.
- **Speech-to-text:** free, it runs on your computer.

## Configuration

`config.example.yaml` documents every setting. The ones you are most likely to change:

| Setting | Meaning |
|---|---|
| `timezone` | IANA name such as `Europe/Madrid`. Decides which day "today" is. |
| `slack.allowed_user_ids` | Slack member IDs of everyone who may use the bot. |
| `sheets.sheet_id`, `sheets.tab` | Which sheet and tab to write to. |
| `sheets.columns` | The header text of the date, amount, category and description columns. |
| `stt.language` | Voice note language, such as `en` or `es`. `auto` lets whisper guess. |
| `stt.model_path` | The whisper model file. |
| `extract.example_rows` | How many recent rows Claude sees as examples (default 30). |

## Troubleshooting

At startup the bot names the setting to fix. The most common messages:

| What you see | What to do |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_FILE is not set` | Set it in `.env`; see [Google Sheets setup](#google-sheets-setup). |
| `no spreadsheet with this ID is shared with ...` | Check `sheets.sheet_id`, and share the sheet with that email. |
| `Google refused access ...` | Share the sheet with the service account as Editor, and check that the Google Sheets API is enabled in the project the key belongs to. |
| `no tab named ...` | Set `sheets.tab` to one of the tab names listed in the message. |
| `no header ... in row 1` | Set `sheets.columns` to the exact header text; the message lists the headers it found. |
| `Dropdown NOT readable` (from `try_sheets.py`) | List your categories in `sheets.fallback_categories`, spelled exactly as in the sheet. |
| `checking SLACK_BOT_TOKEN: Slack rejected it` | Copy the Bot User OAuth Token again; reinstalling the app can change it. |
| `connecting with SLACK_APP_TOKEN: ... invalid_auth` | Copy the app-level token again, or generate a new one with `connections:write`. |
| `missing_scope: add im:read` | Your Slack app predates catch-up. See [Updating an existing app](#updating-an-existing-app). |
| `missing_scope: add ...` (another scope) | Add that scope under **OAuth & Permissions**, then reinstall the app. |
| `Slack sent a login page instead of the file` | The app lacks `files:read`: add it and reinstall. |
| The bot never answers | Check that it is running and that the person's member ID is in `slack.allowed_user_ids`; the log shows `Ignored a direct message from Slack user ...` when it is not. |
| Only some messages get answers | Two copies of the bot are running with the same Slack app. Stop one. |
| Answers come late | The computer was asleep, or the bot was stopped. On macOS, check `deploy/macos/service.sh status`. |
| A write fails with `exceeds grid limits` | The tab ran out of rows. In Google Sheets, add rows at the bottom (make sure the category dropdown covers them), then send the expense again. |
| `whisper-cli failed with exit code -4` (Linux) | Illegal instruction: `whisper-cli` was built for another CPU. Build on the server, or build with `GGML_NATIVE=OFF`. |
| `Permission denied` on `/data` (Docker) | The data folder is not owned by user ID 10001. Run the `chown` command again. |
| `command not found: whisper-cli` (systemd) | Check `ls -l /usr/local/bin/whisper-cli`. If it is elsewhere, put its full path in `stt.whisper_cli`. |

## Design decisions

Why the bot works the way it does, for anyone who wants to change it.

| Decision | Why |
|---|---|
| Slack direct messages over Socket Mode | Already on everyone's phone; no public URL or open port. Slack's incoming webhooks cannot receive audio. WhatsApp needs Meta business verification or unofficial libraries. |
| Speech-to-text runs locally with whisper.cpp | Audio stays on your machine, and the Claude API takes text and images, not audio. Parakeet was considered; whisper.cpp was simpler to run on different hardware. |
| Claude Haiku with structured output; the category is a closed list built from the sheet's dropdown | Claude cannot invent a category, and the value always matches a dropdown option. |
| The last 30 rows are sent as examples | Claude learns your naming habits, such as a store written without its accent or a subscription filed under a specific category. |
| Questions go in the thread, and the whole thread is re-read on each reply | No conversation state is stored, and only a complete entry is written. |
| Mark-first duplicate store: a message is claimed before anything happens and never retried automatically | Slack can deliver an event twice, and catch-up looks at messages again. A missing row is visible (no confirmation), a duplicate row is silent. Reading the sheet to find duplicates was rejected: two same-day purchases of the same amount would look identical. |
| The confirmation shows the row as read back from the sheet | It shows what is really stored, so a wrong date format, a mangled value or a misheard amount is visible. |
| An explicit list of Slack member IDs | Otherwise anyone who can message the bot writes to a finance sheet. Admitting the whole workspace would also admit anyone invited later, guests included. |
| A Google service account the sheet is shared with | The bot can open only what you share with it, asks only for Sheets access, and needs no sign-in flow. |
| Nothing about a sheet is written in code: `init` maps the headers, and categories are read from the dropdown at runtime | Any sheet in any language works, and the repo holds no personal data. |
| Four fixed roles, found by header text | Reordering columns or adding new ones breaks nothing. Extra fields, such as a payment method, are out of scope. |
| `init` guesses columns from what the cells hold, not from header words | Works in any language without word lists. |
| No slang or locale word lists | The model handles spoken numbers. One generic rule says to read separators (dot or comma) the way the user's language and the example rows write numbers. |
| Amounts are exact decimals in any currency; the only check is "more than zero" | A minimum amount cannot work across currencies, and many currencies have cents. |
| The date is the day the expense happened: from the message or receipt, otherwise the day the thread started, in the configured timezone. A future date gets a question; Claude asks to confirm one more than 60 days back. | A receipt photographed days later or a note about "yesterday" gets the right day, and so does a late-night note handled after midnight. The 60-day rule is in the prompt rather than the code, because a code check would ask again after every "yes". |
| Dates are written as serial numbers with the number format of the row above | A date written as text can swap day and month in a US-locale sheet, and many sheets format each cell rather than the whole column, so a bare serial would show as a raw number. |
| One all-or-nothing write of four cells in an explicit next row; values are literal | Other content beside or below the table is never touched, a failed write leaves no half row, and text starting with `=` stays text. |
| One message at a time | Two quick replies in one thread would otherwise both read the thread and log the expense twice. A household sends a few messages a day, so the wait does not matter. |
| A reply in a thread that is already logged logs nothing | Two signs, each covering a gap in the other: the duplicate store, and the bot's confirmation in the thread, which is still there after the store forgets old entries. |
| Fixed replies, without calling Claude, when the newest message has nothing to read; Slack's markup is undone | Calling Claude would only repeat its last question. Markup such as `&amp;` or a link wrapper would otherwise land in the sheet. |
| Questions follow the user's language; the few fixed replies are English; no language setting | Works for anyone without configuration, at the cost of a mixed-language thread. |
| Catch-up runs at startup and every 5 minutes | A macOS service keeps running through sleep, so catching up only at startup would never see messages sent while the Mac slept. The first start skips older messages, and it never looks back as far as the duplicate store's retention, or a forgotten message could be logged twice. It needs only `im:read`: Slack's own error also lists three channel scopes the bot must not have. |
| The macOS service runs a copy of the code from its own data folder | Editing the checkout or switching branches never changes the running bot, and nothing it reads lives in `~/Documents`, which macOS privacy rules can block for background jobs. |
| No keep-awake by default; away mode on demand | A MacBook on battery should sleep normally. Away mode is for when you need answers while you are out. |
| Running out of rows is not handled in code | Rows added through the API would lack the category dropdown, so new entries would show plain text instead of chips. Adding rows in Sheets is quick. |
| Tests use fakes only, with no audio fixtures | Speech-to-text accuracy is judged in real use, not with recorded samples. |
| MIT license; no code copied from copyleft projects | Model files are data, not code, so using them is fine. |

## Development

```sh
uv sync
uv run pytest        # unit tests; no network, keys or audio needed
uv run ruff check
```

Code rules: small single-purpose files (under 100 lines; a test fails at 150), no barrel files (every `__init__.py` stays empty), everything in English, Python 3.12 managed by uv. CI runs the tests on Linux and macOS.

Live checks against your own setup (they use your real keys):

- `uv run python scripts/try_sheets.py` reads your sheet; `--append` also writes a test row. `--config` and `--env` pick other files.
- `uv run python scripts/try_slack.py` echoes what the bot receives, without touching the sheet.
- `uv run python scripts/eval_extract.py evals/extract_cases.yaml` runs about 25 example phrases through Claude. It costs real money, about a cent.

Not built yet: undoing or editing the last row from Slack, a monthly summary, another speech-to-text backend behind the same interface, splitting a receipt into line items, and making speech-to-text optional for text-only setups.

## License

[MIT](LICENSE)
