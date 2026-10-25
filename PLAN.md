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
| Dedupe | Small SQLite store keyed by Slack message ID | Slack retries must not create duplicate rows. |
| Confirmation | After the sheet write succeeds, the bot replies in the thread showing what was recorded: the row is read back from the sheet and shown (row number, date, Valor, Concepto, Descripcion) | Decided 2026-10-25. Reading back shows what is really stored, so a wrong date locale or a mangled value is visible. If the write fails, the reply says so and never claims it was logged. |
| Testing | Unit tests with fakes only; no audio fixtures or STT evals | Decided 2026-10-25. Mauro will use the real bot as soon as the MVP works and tweak from real failures. |
| Security | Only Mauro's Slack user ID may trigger the bot | Otherwise anyone who can DM the bot writes to a finance sheet. |
| Sheets access | Google service account (JSON key), sheet shared with its email | Key lives outside the repo. |
| Develop against | A duplicate of the real sheet | Switch to the real one only at the end (step 10). |
| Licensing | VoiceInk is GPLv3: do not copy its code | Using the same model file is fine. The repo license is Mauro's choice (step 10). |

## The sheet

Four columns, header on row 1, filters on:

| Col | Name | Type | Notes |
|---|---|---|---|
| A | `Fecha` | date, shown `dd/mm/yyyy` | Taken from system time in `America/Bogota` (UTC-5). Never from the speaker. |
| B | `Valor` | number | Integer COP. Display format `$#,###` is already on the sheet; write a plain number. |
| C | `Concepto` | dropdown chip | One of: Carro, Comida, Servicios, Educación, Salud, Perro, Personales, Herramientas, Impuestos, Recreación, Libranza, Donación. Exact spelling, accents included. |
| D | `Descripcion` | free text | Short merchant or item: `Ktronix`, `Exito`, `Arriendo`, `Baño`. |

Traps to handle:
- Writing a date as text like `05/10/2026` can be parsed as May 10 if the sheet locale is US. Write a serial number and verify.
- Column F and below the table may contain other content (the cursor was on F223). Append to an explicit next empty row in A:D, never rely on auto table detection.
- Amounts are spoken in Colombian Spanish: `veinte mil`, `20 lucas`, `dos palos`, `un millón doscientos`. Amounts under about 1,000 COP are suspicious: ask a follow-up instead of logging.

## Environment facts (verified 2026-10-25, macOS arm64, Apple M4)

- `whisper-cli` at `/opt/homebrew/bin/whisper-cli` (Homebrew, Metal backend). `ffmpeg` and `uv` also in `/opt/homebrew/bin`.
- Model: `~/Library/Application Support/com.prakashjoshipax.VoiceInk/WhisperModels/ggml-large-v3-turbo-q5_0.bin`. For other users the README must explain downloading it from the whisper.cpp model repository; the path is configurable.
- Tested: 16 kHz mono wav from ffmpeg, `whisper-cli -m <model> -f <wav> -nt -l auto`, a long Spanish clip transcribed correctly in about 13 s wall time.
- System `python3` is 3.14.5: do not use it for the project.
- Sibling repo `../VoiceInk` exists (reference only).

## Target layout

Each line is one file. Keep it this way when adding code.

```
src/speech_to_sheets/
  config/    settings.py categories.py
  slack/     client.py allowlist.py files.py thread.py replies.py
  stt/       convert.py whisper.py
  extract/   schema.py prompt.py client.py sanity.py
  sheets/    client.py examples.py dates.py append.py read_row.py
  dedupe/    store.py
  pipeline/  bundle.py handle_message.py
  main.py
tests/       one test file per module, plus test_file_length.py
docs/        setup-slack.md  setup-google.md
```

Flow: Slack DM event, then allowlist check and dedupe, then `bundle` (text + transcripts + images), then `extract` (Claude), then `sanity`. If complete: `sheets.append`, then `sheets.read_row` reads the written row back, then a Slack thread reply shows what was recorded, for example `Logged in row 224: 05/10/2026 | $38,921 | Herramientas | Upwork`. If the entry is incomplete: reply with a question in the thread. If the write fails: reply with the error and do not say it was logged.

## Steps

### [x] 1. Scaffold
Create the project skeleton with `uv` (Python 3.12 pinned). Dependencies: `slack-bolt`, `gspread`, `google-auth`, `anthropic`, `pydantic`, `pyyaml`, `python-dotenv`; dev: `pytest`, `ruff`. Add `.gitignore` (at least `.env`, `config.yaml`, `*.json` keys, `*.wav`, `*.m4a`, `*.mp4`, `*.png`, `*.sqlite*`, `.venv`, `__pycache__`), `.env.example`, `config.example.yaml`, empty `__init__.py` files, and `tests/test_file_length.py` that fails when any `.py` file exceeds 150 lines and prints those over 100.
**Acceptance:** `uv run pytest` passes; `uv run ruff check` is clean; `git status` shows no secrets or ignored artefacts staged.

### [ ] 2. Config and secrets
`config/settings.py` loads env vars (`.env` via python-dotenv) and `config.yaml`; `config/categories.py` exposes the Concepto list from config. Settings: Slack bot/app tokens, allowed Slack user ID, Anthropic key, Google key path, sheet ID and tab name, whisper model path, timezone. Fail fast with a clear message when something is missing; never log secret values.
**Acceptance:** unit tests for missing/invalid config; `config.example.yaml` contains the 12 categories.

### [ ] 3. Speech-to-text (whisper)
`stt/convert.py`: ffmpeg to 16 kHz mono wav (accept whatever Slack sends: m4a, mp4, ogg, etc.). `stt/whisper.py`: run `whisper-cli` via `subprocess` (no shell string building), return the transcript text, timeout, clear error if the binary or model is missing. Default `-l es` since voice notes are Spanish only (make it configurable). Treat an empty or near-empty transcript as "no speech", never as an expense.
Do NOT write, generate or record audio tests or fixtures (Mauro's rule): no `say`-generated files, no sample recordings, no STT accuracy eval. Unit-test only with the subprocess mocked (command built correctly, timeout, missing binary or model, empty transcript). Accuracy is judged by Mauro using the real bot once the MVP works; if it fails he will tweak (for example `-l`, whisper's `--prompt`) from real failures.
**Acceptance:** unit tests pass with `subprocess` mocked; no audio files exist in the repo.

### [ ] 4. Extraction (Claude)
`extract/schema.py`: result is either `Complete{valor:int, concepto:enum, descripcion:str}` or `NeedsInfo{question:str, partial}`. The enum is built at runtime from config. `extract/prompt.py`: English instructions, Spanish examples; includes the sheet rows as few-shot. `extract/client.py`: call `claude-haiku-5-5` with structured output (`output_config.format`) and image blocks when present; set `output_config.effort` to `low` (Haiku 5.5 defaults to `medium` with thinking on); do not send `temperature`/`top_p`/`top_k` or an assistant prefill. Check the live API docs before writing the call; the SDK drifts. `extract/sanity.py`: category must be in the enum, `valor` must be positive, under about 1,000 COP triggers a follow-up.
**USER:** needs an Anthropic Console API key with a small prepaid balance and a monthly spend limit.
**Acceptance:** unit tests with a fake client cover slang amounts, missing amount, unknown category, image input; a live eval script over about 20 phrases is run once and results noted in the Status log.

### [ ] 5. Google Sheets
`sheets/client.py` (service account auth), `sheets/examples.py` (read last N rows), `sheets/dates.py` (Bogota date to serial number), `sheets/append.py` (find next empty row in A:D, write the four values, return the row number), `sheets/read_row.py` (read that row back as displayed, for the confirmation message).
**USER:** create a Google Cloud service account and JSON key, duplicate the real sheet, share the duplicate with the service account email. The agent writes `docs/setup-google.md` with exact steps. If the Google account is a Workspace org, key creation may be blocked by policy: report it.
**Acceptance:** append a row to the duplicate; confirm date displays `dd/mm/yyyy`, Valor is numeric and formatted, the Concepto chip renders, nothing in column F onwards is touched.

### [ ] 6. Dedupe store
`dedupe/store.py`: SQLite file (gitignored) mapping Slack message ID to sheet row, with `seen()` and `record()`.
**Acceptance:** tests for first seen, repeat seen, and persistence across restarts.

### [ ] 7. Slack app
Write `slack-app-manifest.yaml` and `docs/setup-slack.md`. Needs: Socket Mode, Messages tab enabled in App Home, event `message.im`, scopes `im:history`, `files:read`, `chat:write`.
**USER:** create the Slack app from the manifest, install it, copy the bot token (`xoxb-`) and app-level token (`xapp-`) into `.env`, give the agent their Slack user ID.
Code: `slack/client.py` (Bolt app), `slack/allowlist.py`, `slack/files.py` (download with the bot token in the Authorization header), `slack/thread.py` (rebuild a thread), `slack/replies.py`.
**Acceptance:** the bot connects and echoes a test DM from Mauro's phone; messages from any other user are ignored; unit tests for allowlist and thread rebuilding.

### [ ] 8. Pipeline and entry point
`pipeline/bundle.py` (text + transcripts + images into one extraction input), `pipeline/handle_message.py` (orchestrator: allowlist, dedupe, bundle, extract, sanity, append, read the row back, send the confirmation or the follow-up question), `main.py` (wire and start). The confirmation is sent only after the append succeeded; the dedupe record is written at the same point.
**Acceptance:** with fakes for Slack, whisper, Claude and Sheets, tests cover: text only, voice only, photo only, `NeedsInfo` then a follow-up reply completing it, confirmation text shows the values read back from the sheet, write failure sends an error and no confirmation, duplicate event ignored, empty transcript, non-allowlisted user.

### [ ] 9. Real use on the duplicate sheet (MVP check)
**USER:** use the bot from the phone as in daily life: text, voice notes, receipt photos, a follow-up. Mauro tweaks from real failures; the agent only fixes what he reports and records findings (accuracy, latency, odd transcripts) in the Status log. No synthetic audio testing.
**Acceptance:** Mauro confirms the four flows write correct rows and each confirmation message matches the sheet.

### [ ] 10. Run as a service, docs, go live
- On start, catch up on DMs received while the Mac was asleep (Socket Mode can drop events), using the dedupe store to avoid repeats.
- `launchd` agent with logs outside the repo; document `caffeinate` or Energy settings for sleep.
- English `README.md` (what it is, setup, privacy note about which data goes to Anthropic).
- **USER:** choose the repo license; confirm switching `sheet ID` from the duplicate to the real sheet.
**Acceptance:** reboot the Mac, send a note, row appears; README setup steps work on a clean checkout.

## Later (not planned)

Undo or edit the last row from Slack, monthly summary, alternative STT backend (Parakeet) behind the same interface, receipt line-item splitting.

## Open questions

- Repo license (step 10).
- Whether to keep the SQLite dedupe file or derive dedupe from sheet contents (default: SQLite).

## Status log

Append newest at the bottom. Format: `YYYY-MM-DD: step N: what happened, what is left`.

- 2026-10-25: planning done. Whisper chosen over Parakeet. No code written yet. Next: step 1.
- 2026-10-25: plan updated: no audio tests or STT evals (Mauro tests with the real bot); confirmation reply shows the row read back from the sheet after a successful write.
- 2026-10-25: step 1 done. `uv` project with Python 3.12 (`.python-version`), deps installed (slack-bolt, gspread, google-auth, anthropic, pydantic, pyyaml, python-dotenv; dev: pytest, ruff), empty packages under `src/speech_to_sheets/`, `.gitignore`, `.env.example` (secrets only: Slack tokens, Anthropic key, Google key path), `config.example.yaml` (everything non-secret: timezone, allowed Slack user ID, sheet ID and tab, whisper CLI and model path, language, model name, example row count, the 12 categories). Two guard tests: `test_file_length.py` (fails over 150 lines, warns over 100) and `test_no_barrel_files.py` (every `__init__.py` must be empty); both verified to fail on a violation. `uv run pytest` 3 passed, `uv run ruff check` clean. The script entry `speech_to_sheets.main:main` does not exist yet (step 8). Next: step 2.
