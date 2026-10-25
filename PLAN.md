# speech-to-sheets: project plan

Log expenses into a Google Sheet by sending a voice note, text or receipt photo to a Slack DM.

## For agents: read this first

This file is the source of truth. Several agents may work on this project in sequence.

1. Read this whole file, then `git status` / list the repo to see what actually exists. If the repo and this file disagree, trust the repo and fix this file.
2. Work on the first unchecked step in order. Do not skip ahead; later steps depend on earlier ones.
3. A step is done only when its **Acceptance** checks pass. Run them, do not assume. Then tick the box and add a line to the **Status log**.
4. If you stop mid-step, write exactly where you stopped and what is left in the Status log. Leave the box unticked.
5. Steps marked **USER** need something only Mauro can do (accounts, keys, phone). Ask for it; do not invent credentials or stub them silently.
6. NEVER run `git commit`, `git push` or anything that creates a commit. When a step finishes, suggest a commit message for Mauro (rules are in his global CLAUDE.md).
7. Respect the **Code rules** below. A test enforces the file-size rule.
8. Never put secrets, audio recordings, sheet screenshots or personal data in the repo. This repo will be public.

## Code rules (set by Mauro)

- Small, single-responsibility files. Aim for under 100 lines. 150 lines is unacceptable.
- No barrel files: every `__init__.py` stays empty; import from the module that defines the thing.
- Orchestration files (wiring modules together) are welcome.
- Code, comments, README, prompts and logs in English. Spanish appears only in the category config and in example phrases.
- Python 3.12 managed by `uv`. The system default is 3.14, which many libraries do not support yet.

## Decisions already made

| Topic | Decision | Why / notes |
|---|---|---|
| Chat transport | Slack DM, Socket Mode (`slack_bolt`) | Already on Mauro's phone. No public URL or open port. Slack incoming webhooks cannot receive audio, so no webhook. |
| Rejected transports | WhatsApp, Telegram | WhatsApp needs Meta business verification or unofficial libraries; Telegram was offered but Mauro prefers Slack. |
| Speech-to-text | Local `whisper-cli` (whisper.cpp) with `ggml-large-v3-turbo-q5_0.bin` | Decided 2026-10-25. Mauro found it less finicky on hardware than Parakeet. Verified working here. |
| Rejected STT | Parakeet v3 (parakeet-mlx, FluidAudio) | VoiceInk's copy is Core ML for Swift, not usable from Python; parakeet-mlx untested. Can be revisited later behind the same interface. |
| Audio input to Claude | Not possible | The Messages API takes text, images and PDFs, not audio. So STT stays local and Claude only sees text and images. (Not re-verified against live docs.) |
| Extraction model | Anthropic API, `claude-haiku-5-5` | The Max plan does not cover API calls. Needs a Console API key, paid separately; cost is cents per month. Agent SDK credit on Max exists but was rejected: heavy, experimental-use only, unusable for others. |
| Extraction method | Structured output with `Concepto` as a closed enum | Claude cannot invent a category; value matches the dropdown exactly. |
| Personalisation | Last ~30 sheet rows given to Claude as few-shot examples | Learns Mauro's naming (`Exito` without accent, `Claude` is `Herramientas`). Those rows are sent to the Anthropic API. |
| Receipts | Photos go to Claude as images in the same call | |
| Follow-ups | Bot asks in the Slack thread when unsure; reply by text or voice. Thread is re-read via `conversations.replies`, so no conversation state is stored. | Only write to the sheet when the entry is complete. |
| Dedupe | Small local SQLite store keyed by Slack message ID. Mark-first (at-most-once): claim the message as `pending` before doing anything, then `done` (with row number) or `failed`; never retry automatically, the user resends. Entries older than `dedupe.retention_days` (default 30) are deleted on startup. | Decided 2026-10-25. Slack can redeliver events (reconnects) and step 10 catch-up replays DMs, so repeats must not create duplicate rows. A missing row is visible (no confirmation) while a duplicate is silent. The store is never sent to Claude, so it costs no tokens; pruning is hygiene. Rejected: deduping by reading the sheet (no ID column; same-day same-amount purchases would be falsely rejected), Slack reactions as memory, memory-only. |
| Confirmation | After the sheet write succeeds, the bot replies in the thread showing what was recorded: the row is read back from the sheet and shown (row number, date, Valor, Concepto, Descripcion) | Decided 2026-10-25. Reading back shows what is really stored, so a wrong date locale or a mangled value is visible. If the write fails, the reply says so and never claims it was logged. |
| Testing | Unit tests with fakes only; no audio fixtures or STT evals | Decided 2026-10-25. Mauro will use the real bot as soon as the MVP works and tweak from real failures. |
| Security | Only Mauro's Slack user ID may trigger the bot | Otherwise anyone who can DM the bot writes to a finance sheet. |
| Sheets access | Google service account (JSON key), sheet shared with its email | Key lives outside the repo. |
| Develop against | A duplicate of the real sheet | Switch to the real one only at the end (step 10). |
| Licensing | VoiceInk is GPLv3: do not copy its code | Using the same model file is fine. The repo license is MIT, chosen by Mauro when he created the GitHub repo (`krsmauro/speech-to-sheets`, 2026-10-25); the `LICENSE` file lives on the remote `main`. |
| No personal data in the repo | Column headers and categories are never hardcoded. Headers are mapped by the `speech-to-sheets init` command (connects to the sheet, proposes a mapping, asks to confirm) and stored in `config.yaml`; categories are read from the category column's dropdown at runtime, with `sheets.fallback_categories` in config as a fallback. All config keys and defaults are in English. | Decided 2026-10-25. Mauro's categories are already in the first pushed commit and he accepts that, but the final version must not contain them (step 11). |
| Column mapping | Four fixed roles: date, amount, category, description, set in config as `sheets.columns` (role to header text in row 1). The bot finds columns by header text, writes only to those columns, and finds the next empty row from the date column. | Reordering columns or extra columns on the sheet break nothing. Arbitrary extra fields (payment method, etc.) are out of scope for now. |
| Slang and locale hints | None. No slang lists or per-locale hint files. | Decided 2026-10-25 by Mauro. The model handles plain spoken numbers; he tunes from real use. Language, timezone and the minimum-amount check are plain config values. |
| Deployment | Mac first; later an always-on cheap Linux server | Socket Mode needs no inbound ports. Sizing notes below. |

## Mauro's sheet (development reference only)

> Personal example used while developing. The code must read headers and categories from the connected sheet and never hardcode them. Step 11 removes these details from the repo.

Four columns, header on row 1, filters on:

| Col | Name | Type | Notes |
|---|---|---|---|
| A | `Fecha` | date, shown `dd/mm/yyyy` | Taken from system time in `America/Bogota` (UTC-5). Never from the speaker. |
| B | `Valor` | number | Integer COP. Display format `$#,###` is already on the sheet; write a plain number. |
| C | `Concepto` | dropdown chip | One of: Carro, Comida, Servicios, Educación, Salud, Perro, Personales, Herramientas, Impuestos, Recreación, Libranza, Donación. Exact spelling, accents included. |
| D | `Descripcion` | free text | Short merchant or item: `Ktronix`, `Exito`, `Arriendo`, `Baño`. |

Traps to handle:
- Writing a date as text like `05/10/2026` can be parsed as May 10 if the sheet locale is US. Write a serial number and verify.
- Column F and below the table may contain other content (the cursor was on F223). Append to an explicit next empty row in the four mapped columns, never rely on auto table detection.
- Amounts are spoken as plain numbers (for example `veinte mil`). Mauro's sheet is in COP, so amounts under 1,000 are suspicious: `sanity.min_amount` (default 0 = off, Mauro sets 1000) makes the bot ask a follow-up instead of logging.

## Environment facts (verified 2026-10-25, macOS arm64, Apple M4)

- `whisper-cli` at `/opt/homebrew/bin/whisper-cli` (Homebrew, Metal backend). `ffmpeg` and `uv` also in `/opt/homebrew/bin`.
- Machine: Apple M4, 10 cores, 24 GB RAM.
- Model: `~/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo-q5_0.bin` (547 MB). For other users the README must explain downloading it from the whisper.cpp model repository; the path is configurable.
- Tested: 16 kHz mono wav from ffmpeg, `whisper-cli -m <model> -f <wav> -nt -l auto`, a long Spanish clip transcribed correctly in about 13 s wall time.
- System `python3` is 3.14.5: do not use it for the project.
- Sibling repo `../VoiceInk` exists (reference only).

## Deployment notes (cheap always-on Linux server)

Estimates from general knowledge, NOT measured. Step 11 includes a benchmark on the real server.

- **No inbound ports needed** (Socket Mode). Firewall everything except SSH. Run as a non-root user, `chmod 600` the Google key and the env file, load secrets through the service manager's environment file, enable automatic security updates.
- **With local speech-to-text:** the model file is 547 MB and whisper.cpp needs roughly 1 to 1.5 GB of RAM with it loaded, so aim for 2 vCPU, 4 GB RAM, 20 GB disk (2 GB RAM plus swap may work). Without a GPU, transcription is much slower than the 13 s measured on the M4; a short voice note could take tens of seconds on 2 vCPUs. x86 or ARM both work; build whisper.cpp natively on the server. Smaller or more quantized models (`small`, `base`) trade accuracy for speed.
- **Without speech-to-text** (text and photos only) the process is mostly idle and 512 MB to 1 GB of RAM is enough.
- **A hosted transcription API** would allow a tiny server but sends audio to a third party. Not chosen; Anthropic has no audio input.
- A Docker image that builds whisper.cpp is planned for portability (step 11). It is for servers; on a Mac, Docker cannot use the GPU, so run natively there.

## Target layout

Each line is one file. Keep it this way when adding code.

```
src/speech_to_sheets/
  config/    settings.py sections.py columns.py secrets.py errors.py
  slack/     client.py allowlist.py files.py thread.py replies.py
  stt/       run.py convert.py whisper.py transcript.py voice_note.py check.py errors.py
  extract/   schema.py prompt.py client.py sanity.py
  sheets/    client.py schema.py examples.py dates.py append.py read_row.py
  dedupe/    store.py prune.py
  pipeline/  bundle.py handle_message.py
  cli/       init.py prompts.py write_config.py
  main.py
tests/       one test file per module, plus test_file_length.py
docs/        setup-slack.md  setup-google.md  deployment.md
deploy/      launchd and systemd examples, Dockerfile (step 11)
```

Flow: Slack DM event, then allowlist check and dedupe, then `bundle` (text + transcripts + images), then `extract` (Claude), then `sanity`. If complete: `sheets.append`, then `sheets.read_row` reads the written row back, then a Slack thread reply shows what was recorded, for example `Logged in row 224: 05/10/2026 | $38,921 | Herramientas | Upwork`. If the entry is incomplete: reply with a question in the thread. If the write fails: reply with the error and do not say it was logged.

## Steps

### [x] 1. Scaffold
Create the project skeleton with `uv` (Python 3.12 pinned). Dependencies: `slack-bolt`, `gspread`, `google-auth`, `anthropic`, `pydantic`, `pyyaml`, `python-dotenv`; dev: `pytest`, `ruff`. Add `.gitignore` (at least `.env`, `config.yaml`, `*.json` keys, `*.wav`, `*.m4a`, `*.mp4`, `*.png`, `*.sqlite*`, `.venv`, `__pycache__`), `.env.example`, `config.example.yaml`, empty `__init__.py` files, and `tests/test_file_length.py` that fails when any `.py` file exceeds 150 lines and prints those over 100.
**Acceptance:** `uv run pytest` passes; `uv run ruff check` is clean; `git status` shows no secrets or ignored artefacts staged.

### [x] 2. Config and secrets
`config/settings.py` loads env vars (`.env` via python-dotenv) and `config.yaml`; `config/columns.py` holds the role-to-header mapping (`sheets.columns`). Settings: Slack bot/app tokens, allowed Slack user ID, Anthropic key, Google key path, sheet ID and tab name, `sheets.columns`, `sheets.fallback_categories`, whisper CLI, model path and language (default `auto`), timezone (default `UTC`), `sanity.min_amount` (default 0 = off), `dedupe` settings. All keys and defaults are in English; see `config.example.yaml`. Fail fast with a clear message when something is missing; never log secret values.
**Acceptance:** unit tests for missing/invalid config and defaults; `config.example.yaml` contains only generic example values (no personal categories or paths).

### [x] 3. Speech-to-text (whisper)
`stt/convert.py`: ffmpeg to 16 kHz mono wav (accept whatever Slack sends: m4a, mp4, ogg, etc.). `stt/whisper.py`: run `whisper-cli` via `subprocess` (no shell string building), return the transcript text, timeout, clear error if the binary or model is missing. The language comes from config (`stt.language`, default `auto`; Mauro sets `es`). Treat an empty or near-empty transcript as "no speech", never as an expense.
Do NOT write, generate or record audio tests or fixtures (Mauro's rule): no `say`-generated files, no sample recordings, no STT accuracy eval. Unit-test only with the subprocess mocked (command built correctly, timeout, missing binary or model, empty transcript). Accuracy is judged by Mauro using the real bot once the MVP works; if it fails he will tweak (for example `-l`, whisper's `--prompt`) from real failures.
**Acceptance:** unit tests pass with `subprocess` mocked; no audio files exist in the repo.

### [ ] 4. Extraction (Claude)
`extract/schema.py`: result is either `Complete{valor:int, concepto:enum, descripcion:str}` or `NeedsInfo{question:str, partial}`. The enum is built at runtime from the categories read from the sheet (`sheets/schema.py`). `extract/prompt.py`: English instructions only, no slang or locale hints; the sheet's own last rows are the few-shot examples, in whatever language the user writes. `extract/client.py`: call `claude-haiku-5-5` with structured output (`output_config.format`) and image blocks when present; set `output_config.effort` to `low` (Haiku 5.5 defaults to `medium` with thinking on); do not send `temperature`/`top_p`/`top_k` or an assistant prefill. Check the live API docs before writing the call; the SDK drifts. `extract/sanity.py`: category must be in the enum, the amount must be positive, and below `sanity.min_amount` (when set) triggers a follow-up.
**USER:** needs an Anthropic Console API key with a small prepaid balance and a monthly spend limit.
**Acceptance:** unit tests with a fake client cover spoken-number amounts, missing amount, unknown category, image input; a live eval script over about 20 phrases is run once and results noted in the Status log.

### [ ] 5. Google Sheets
`sheets/client.py` (service account auth), `sheets/schema.py` (read row 1 and locate each role's column by its header text; read the category column's dropdown options from its data validation; fresh read on every message, no cache; fail with a clear message listing the headers found if one is missing; confirm against Mauro's duplicate that the Sheets API really returns the chip values, otherwise use `sheets.fallback_categories`), `sheets/examples.py` (read last N rows), `sheets/dates.py` (date in the configured timezone to serial number), `sheets/append.py` (find next empty row from the date column, write only the four mapped columns, return the row number), `sheets/read_row.py` (read that row back as displayed, for the confirmation message).
**USER:** create a Google Cloud service account and JSON key, duplicate the real sheet, share the duplicate with the service account email. The agent writes `docs/setup-google.md` with exact steps. If the Google account is a Workspace org, key creation may be blocked by policy: report it.
**Acceptance:** append a row to the duplicate; confirm date displays `dd/mm/yyyy`, Valor is numeric and formatted, the category chip renders, nothing outside the mapped columns is touched; the categories read from the sheet match the dropdown.

### [ ] 5b. Init command
`uv run speech-to-sheets init` creates `config.yaml` interactively. `cli/init.py` (orchestrator), `cli/prompts.py` (ask, confirm and choose helpers, injectable so tests can script answers), `cli/write_config.py` (writes `config.yaml`; asks before overwriting; never writes secrets). Flow: load the secrets from `.env`, connect to the sheet ID given, list tabs and ask which one, read row 1, propose a role-to-header mapping by best guess (names like date, amount, category, description in any language) and let the user confirm or pick from the headers found, read and show the dropdown options of the category column (if unreadable, ask for a list to store as `fallback_categories`), ask timezone and STT language, write `config.yaml`. `main.py` dispatches the `init` subcommand (wired in step 8).
**Acceptance:** tests with scripted answers and a fake sheet cover a clean mapping, a wrong guess corrected by the user, unreadable dropdown, existing config not overwritten without confirmation; run once against Mauro's duplicate sheet and the generated config works.

### [ ] 6. Dedupe store
`dedupe/store.py`: SQLite file (gitignored), table of Slack message ID, status (`pending`, `done`, `failed`), sheet row and created-at. API: `claim(message_id) -> bool` (atomic insert, `False` if already present), `finish(message_id, row)`, `fail(message_id)`. `dedupe/prune.py`: `prune(older_than_days)`, called once at startup. The `dedupe` section (`retention_days`, `path`) already exists in `config.example.yaml`.
**Acceptance:** tests for first claim, repeat claim, finish and fail, persistence across restarts, and pruning that deletes only old entries.

### [ ] 7. Slack app
Write `slack-app-manifest.yaml` and `docs/setup-slack.md`. Needs: Socket Mode, Messages tab enabled in App Home, event `message.im`, scopes `im:history`, `files:read`, `chat:write`.
**USER:** create the Slack app from the manifest, install it, copy the bot token (`xoxb-`) and app-level token (`xapp-`) into `.env`, give the agent their Slack user ID.
Code: `slack/client.py` (Bolt app), `slack/allowlist.py`, `slack/files.py` (download with the bot token in the Authorization header), `slack/thread.py` (rebuild a thread), `slack/replies.py`.
**Acceptance:** the bot connects and echoes a test DM from Mauro's phone; messages from any other user are ignored; unit tests for allowlist and thread rebuilding.

### [ ] 8. Pipeline and entry point
`pipeline/bundle.py` (text + transcripts + images into one extraction input), `pipeline/handle_message.py` (orchestrator: allowlist, dedupe, bundle, extract, sanity, append, read the row back, send the confirmation or the follow-up question), `main.py` (wire and start). The orchestrator calls `claim()` first and stops if it returns `False`; it calls `finish()` only after the append succeeded (the confirmation is sent after that) and `fail()` on any handled error.
**Acceptance:** with fakes for Slack, whisper, Claude and Sheets, tests cover: text only, voice only, photo only, `NeedsInfo` then a follow-up reply completing it, confirmation text shows the values read back from the sheet, write failure sends an error and no confirmation, duplicate event ignored, empty transcript, non-allowlisted user.

### [ ] 9. Real use on the duplicate sheet (MVP check)
**USER:** use the bot from the phone as in daily life: text, voice notes, receipt photos, a follow-up. Mauro tweaks from real failures; the agent only fixes what he reports and records findings (accuracy, latency, odd transcripts) in the Status log. No synthetic audio testing.
**Acceptance:** Mauro confirms the four flows write correct rows and each confirmation message matches the sheet.

### [ ] 10. Run as a service, docs, go live
- On start, catch up on DMs received while the Mac was asleep (Socket Mode can drop events), using the dedupe store to avoid repeats.
- `launchd` agent with logs outside the repo; document `caffeinate` or Energy settings for sleep.
- English `README.md` (what it is, setup, privacy note about which data goes to Anthropic).
- **USER:** confirm switching `sheet ID` from the duplicate to the real sheet.
**Acceptance:** reboot the Mac, send a note, row appears; README setup steps work on a clean checkout.

### [ ] 11. Portable public release
- English `README.md` aimed at a stranger: what it is, quick start (`init`, secrets, run), per-OS install notes for `whisper-cli` and `ffmpeg` (macOS Homebrew, Linux build or package, Windows release), privacy note about which data goes to Anthropic (transcripts, photos, last rows).
- `deploy/`: launchd plist and systemd unit examples, a Dockerfile that builds whisper.cpp for servers; `docs/deployment.md` with the hardening notes above.
- GitHub Actions workflow running the unit tests on Linux and macOS, so the portability claim is checked. Only macOS is tested by hand.
- Remove Mauro's personal details from the repo: the "Mauro's sheet" section and category names in `PLAN.md` (or reduce `PLAN.md` to a generic contributor plan). The first commit keeps them in history; Mauro accepted that.
- **USER:** on the real server, run one of his real voice notes through `whisper-cli` and note the time and RAM used; decide model size or server size from that.
**Acceptance:** clean checkout on Linux: `init`, run, unit tests green in CI; no personal categories or paths in tracked files (`git grep`).

## Later (not planned)

Undo or edit the last row from Slack, monthly summary, alternative STT backend (Parakeet) behind the same interface, receipt line-item splitting.

## Open questions


## Status log

Append newest at the bottom. Format: `YYYY-MM-DD: step N: what happened, what is left`.

- 2026-10-25: planning done. Whisper chosen over Parakeet. No code written yet. Next: step 1.
- 2026-10-25: plan updated: no audio tests or STT evals (Mauro tests with the real bot); confirmation reply shows the row read back from the sheet after a successful write.
- 2026-10-25: step 1 done. `uv` project with Python 3.12 (`.python-version`), deps installed (slack-bolt, gspread, google-auth, anthropic, pydantic, pyyaml, python-dotenv; dev: pytest, ruff), empty packages under `src/speech_to_sheets/`, `.gitignore`, `.env.example` (secrets only: Slack tokens, Anthropic key, Google key path), `config.example.yaml` (everything non-secret: timezone, allowed Slack user ID, sheet ID and tab, whisper CLI and model path, language, model name, example row count, the 12 categories). Two guard tests: `test_file_length.py` (fails over 150 lines, warns over 100) and `test_no_barrel_files.py` (every `__init__.py` must be empty); both verified to fail on a violation. `uv run pytest` 3 passed, `uv run ruff check` clean. The script entry `speech_to_sheets.main:main` does not exist yet (step 8). Next: step 2.
- 2026-10-25: decisions: MIT license (set on GitHub, LICENSE is on the remote main; local repo has no remote yet, Mauro pushes himself). Dedupe settled as SQLite, mark-first, 30-day pruning (see Decisions table). Next: step 2.
- 2026-10-25: decisions: no personal data in the repo (headers via init command, categories from the sheet dropdown at runtime, config fallback), four fixed roles mapped by header text, no slang or locale hints, all config and defaults in English, cheap Linux server later (sizing in Deployment notes, unmeasured). Added step 5b (init command) and step 11 (portable release). `config.example.yaml` made generic; Mauro personal values moved to his gitignored `config.yaml`. Next: step 2.
- 2026-10-25: step 2 done. `config/` has `settings.py` (`Settings` model plus `load_settings(config_path, env_file, environ)`), `sections.py` (slack, sheets, stt, extract, sanity, dedupe models), `columns.py` (the four role headers, English defaults, must be distinct ignoring case), `secrets.py` (the four env vars; Slack tokens checked for the `xoxb-`/`xapp-` prefix, Google key file must exist), `errors.py` (`ConfigError`, `describe`). Behaviour: real environment variables win over `.env`; an empty variable counts as missing; unknown keys in `config.yaml` are errors (catches typos); secrets inside `config.yaml` are refused; all problems are reported in one `ConfigError`, and error text never contains a secret value (verified by breaking the guard and watching the test fail). Required with no default: `slack.allowed_user_id`, `sheets.sheet_id`, `sheets.tab`, `stt.model_path`. The model file is not checked for existence here (step 3 does that). `tests/` gained `conftest.py` and six `test_config_*.py` files; `config.example.yaml` is checked against the models and for personal values. `uv run pytest` 45 passed, `ruff check` and `ruff format --check` clean, no file over 100 lines. Mauro's `config.yaml` still has `sheets.tab` empty, so it will not load until he fills it in. Next: step 3.
- 2026-10-25: step 3 done. `stt/` has `run.py` (`run_tool`: list arguments, no shell, UTF-8 with replacement, timeout; every failure becomes `SttError` naming the config key to fix; on a non-zero exit it shows the stderr lines starting with "error", because whisper-cli prints its error between backend logs and its full help text), `convert.py` (`to_wav`: ffmpeg to 16 kHz mono pcm_s16le, absolute paths so a file name cannot look like an option), `whisper.py` (`transcribe`: `whisper-cli -m <model> -f <wav> -nt -l <language>`; `-l` is always passed because whisper-cli defaults to English), `transcript.py` (`clean_transcript`: collapses whitespace, returns None when only whitespace, punctuation or tags like `[BLANK_AUDIO]` remain), `voice_note.py` (`transcribe_voice_note(bytes, stt)`: writes the audio to a private temp folder that is always deleted; no file extension, ffmpeg detects the format from content, so no Slack file name is ever used in a path), `check.py` (`check_stt`: startup check for both tools and the model; step 8 should call it in `main.py`). Config gained `stt.ffmpeg` (launchd has a short PATH, so step 10 needs full paths) and `stt.timeout_seconds` (default 120). Tests: `run_tool` against small real Python child processes; ffmpeg and whisper with `run_tool` faked; no audio anywhere. Two mutations (drop `-l`, drop the tag stripping) made the tests fail as they should. Checked against the real tools without audio: `check_stt` passes with Mauro's config; ffmpeg on non-audio bytes and whisper on a missing wav give readable errors, and the temp folder is gone afterwards. Not verified: a real voice note end to end (left to step 9, per Mauro's rule). Whisper sometimes outputs a stock sentence on silence; it is not filtered here (no phrase lists), but it has no amount, so extraction will ask instead of logging. Possible tweaks if real use shows problems: whisper's `--prompt`, `-sns` (suppress non-speech tokens). `uv run pytest` 73 passed, ruff clean. Next: step 4 (needs Mauro's Anthropic key; he says it is now in `.env`).
