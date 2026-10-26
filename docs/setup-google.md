# Google Sheets setup

The bot writes to your sheet through a Google **service account**: a robot Google identity with its own email address. You share the sheet with that address, the same way you would share it with a person. The bot can open only the sheets shared with it, nothing else in your Google Drive.

It takes about 10 minutes. Standard use of the Google Sheets API is free, and the bot makes about seven requests per expense, far under Google's limit of 60 reads and 60 writes per minute.

## 1. Create a Google Cloud project

1. Open the [Google Cloud console](https://console.cloud.google.com/) and sign in.
2. In the project picker at the top, choose **New project**, name it (for example `speech-to-sheets`) and create it.
3. Make sure the new project is selected in the picker before you continue.

## 2. Enable the Google Sheets API

**APIs & Services > Library**, search for **Google Sheets API**, open it and click **Enable**.

The Google Drive API is not needed: the bot opens the sheet by its ID and asks only for Sheets access.

## 3. Create the service account

1. **IAM & Admin > Service accounts > Create service account**.
2. Name it (for example `speech-to-sheets`) and continue.
3. Skip the optional steps that grant roles or access. The account needs no project roles; its only access is the sheet you share with it.
4. Click **Done**.

## 4. Create a JSON key

1. On the **Service accounts** page, click the new account's email address.
2. Open the **Keys** tab, then **Add key > Create new key**.
3. Choose **JSON** and click **Create**. The browser downloads the key file. It can be downloaded only once; if you lose it, create a new key.

If Google says key creation is blocked by an organization policy (`iam.disableServiceAccountKeyCreation`): Google enforces this by default in organizations created on or after 3 May 2024, which is common with Google Workspace accounts. Either create the project with a personal Google account, or ask your Workspace admin to allow keys for this one project.

## 5. Store the key safely

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

## 6. Share the sheet with the service account

1. Find the service account's email: it is the `client_email` value in the key file, and it is also listed on the **Service accounts** page. It ends in `.iam.gserviceaccount.com`.
2. While you set things up, work on a copy of your sheet (**File > Make a copy**) so a mistake cannot touch your real data.
3. In the sheet, click **Share**, paste the email, choose **Editor**, untick **Notify people**, and share.

## 7. Point config.yaml at the sheet

The easy way is to let the bot read your sheet and write `config.yaml` for you:

```sh
uv run speech-to-sheets init
```

It asks for the sheet's URL, lets you pick the tab, proposes which column holds the date, amount, category and description (guessed from what the cells hold, so any header language works; you confirm or correct it), reads the category dropdown, and asks for your timezone, the Slack member IDs of everyone who may use the bot, the whisper model file and voice note language. It needs only `GOOGLE_SERVICE_ACCOUNT_FILE` from `.env`, writes nothing until the last question, and asks before replacing an existing `config.yaml`.

To write it by hand instead, set these in `config.yaml`, under `sheets`:

- `sheet_id`: the long ID in the sheet's URL, `https://docs.google.com/spreadsheets/d/<sheet_id>/edit`.
- `tab`: the name of the tab at the bottom of the sheet.
- `columns`: the exact header text in row 1 for the date, amount, category and description columns. Case and surrounding spaces do not matter. Other columns are ignored and never written.
- `fallback_categories`: leave empty if the category column has a dropdown; the bot reads the options from it. List your categories here only if the check below says the dropdown is not readable.

## 8. Check the connection

```sh
uv run python scripts/try_sheets.py
```

This only reads. It shows the columns it found, the categories from the dropdown and the last few rows.

```sh
uv run python scripts/try_sheets.py --append
```

This writes one test row (today's date, amount 1234, the first category, description `speech-to-sheets test row, delete me`) and reads it back. In the sheet, check that:

- the date shows in your sheet's date format, with the day and month the right way round;
- the amount is a number in your sheet's number format;
- the category shows as a dropdown option, not as plain text;
- nothing else in the sheet changed.

Then delete the test row.

## What the bot reads and writes

- **Reads**, on every message: the headers in row 1, the category dropdown, and the last rows (`extract.example_rows`, default 30). Those rows are sent to Anthropic as examples of how you name things.
- **Writes**: one row per expense, in the four mapped columns only, below the last row that has a date.

## Troubleshooting

| Message | What to do |
|---|---|
| `no spreadsheet with this ID is shared with ...` | Check `sheets.sheet_id`, and share the sheet with that email. |
| `Google refused access ...` | Share the sheet with the service account as Editor, and check that the Google Sheets API is enabled in the project the key belongs to. |
| `no tab named ...` | Set `sheets.tab` to one of the tab names listed in the message. |
| `no header ... in row 1` | Set `sheets.columns` to the exact header text; the message lists the headers it found. |
| `Dropdown NOT readable` | List your categories in `sheets.fallback_categories`, spelled exactly as in the sheet. |
