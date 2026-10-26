# Slack setup

You talk to the bot in a Slack direct message. It runs as a Slack app that you create in your own workspace from the manifest in this repo. It uses **Socket Mode**: the bot opens the connection to Slack itself, so your computer needs no public address and no open port.

It takes about 5 minutes. You need permission to install apps in the workspace; in a free workspace you have it, in a company workspace an admin may have to approve the app.

## 1. Create the app from the manifest

1. Open [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**, then **From a manifest**.
2. Pick your workspace and continue.
3. Choose the **YAML** tab, replace its content with the content of `slack-app-manifest.yaml` from this repo, and continue.
4. Check the summary (three bot scopes: `im:history`, `files:read`, `chat:write`; one event: `message.im`; Socket Mode on) and click **Create**.

You can rename the app first by changing `name` and `display_name` in the manifest.

## 2. Install it and copy the bot token

1. In the app's settings, open **Install App** (or **OAuth & Permissions**) and click **Install to Workspace**, then **Allow**.
2. Copy the **Bot User OAuth Token**. It starts with `xoxb-`.
3. Put it in `.env`:

```sh
SLACK_BOT_TOKEN=xoxb-...
```

## 3. Create the app-level token for Socket Mode

The manifest turns Socket Mode on, but Slack does not create this token for you.

1. Open **Basic Information** and scroll to **App-Level Tokens**.
2. Click **Generate Token and Scopes**, name it (for example `socket`), click **Add Scope**, choose `connections:write`, and click **Generate**.
3. Copy the token. It starts with `xapp-`. Put it in `.env`:

```sh
SLACK_APP_TOKEN=xapp-...
```

Both tokens are passwords for the bot. If one leaks, regenerate it in the same place (**OAuth & Permissions** for the bot token, **App-Level Tokens** for the other).

## 4. Choose who may use it

The bot ignores everyone who is not on its list, so nobody else in the workspace can write to your sheet. A household that shares one sheet lists each person.

1. In Slack, open the person's profile: for yourself, click your profile picture, then **Profile**; for someone else, click their name.
2. Click the three dots (**More**) and **Copy member ID**. It starts with `U`.
3. List every ID in `config.yaml`, or run `uv run speech-to-sheets init`, which asks for them:

```yaml
slack:
  allowed_user_ids: [U0123ABCD, U0456EFGH]
```

To add someone later, add their ID and restart the bot. If a person writes to the bot before they are on the list, the terminal logs `Ignored a direct message from Slack user U...` with their ID.

## 5. Check the connection

```sh
uv run python scripts/try_slack.py
```

In Slack, find the app under **Apps** in the sidebar (or search for its name) and open its **Messages** tab. Each person on the list does this on their own Slack; each gets their own conversation with the bot, and its answers go only to whoever wrote. Send it:

- a short text, such as `test`;
- a voice clip (the microphone button);
- a photo of a receipt;
- a reply in the thread of one of its answers.

The bot answers each one in its thread with what it received: the text length, each file's type and size, whether a photo can be sent to Claude, and the transcript of a voice clip. Nothing is written to the sheet. Stop the script with Ctrl-C.

If the Messages tab says that sending messages to this app is turned off, open **App Home** in the app's settings, make sure **Messages Tab** is on and **Allow users to send Slash commands and messages from the messages tab** is ticked, then restart Slack.

## 6. Start the bot

```sh
uv run speech-to-sheets run
```

It first checks the setup (whisper and ffmpeg, the sheet's headers and categories, the Anthropic key and model) and stops with a message naming what to fix. Then send an expense in the same Messages tab, such as `lunch 12.50`, a voice clip or a receipt photo. The bot answers in the message's thread, either with `Logged in row ...` and the row as the sheet shows it, or with a question.

Answer a question in its thread (tap the reply under it), not as a new message: a new message counts as a new expense. A reply in a thread that is already logged logs nothing. If something fails, the answer says what; replying in that thread tries again. Stop the bot with Ctrl-C.

## What the bot can see

Only direct messages sent to it, and the files in them. It cannot read channels or other people's conversations. Messages from anyone not in `slack.allowed_user_ids` are ignored and never read further.

An app you create in your own workspace counts as an internal app for Slack's rate limits, so the stricter limits Slack introduced in 2025 for commercially distributed apps do not apply.

## Troubleshooting

| Message | What to do |
|---|---|
| `checking SLACK_BOT_TOKEN: Slack rejected it` | Copy the Bot User OAuth Token again; reinstalling the app can change it. |
| `connecting with SLACK_APP_TOKEN: ... invalid_auth` | Copy the app-level token again, or generate a new one with `connections:write`. |
| `missing_scope: add ...` | Add that scope under **OAuth & Permissions**, then reinstall the app. |
| `Slack sent a login page instead of the file` | The app lacks `files:read`: add it and reinstall. |
| The bot never answers | Check that the bot (or the check script) is running and that the person's member ID is in `slack.allowed_user_ids`; the terminal logs `Ignored a direct message from Slack user ...` when it is not. |
