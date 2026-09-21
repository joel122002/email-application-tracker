# Email Application Tracker

This application reads recent messages from a Gmail inbox, uses a local Ollama model to identify job-application emails, and records application status in Google Sheets. Processed Gmail message IDs are stored locally in SQLite so the same messages are not processed again.

## Prerequisites

- Python 3.10 or newer
- An Ollama installation with the `gemma3:12b` model available
- A Google account with access to Gmail and Google Sheets
- A Google Cloud project with the Gmail API and Google Sheets API enabled

## Setup

From the project directory, create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install and start Ollama, then download the model used by `agent.py`:

```bash
ollama pull gemma3:12b
```

Make sure Ollama is running before starting the agent.

## Create `credentials.json`

`credentials.json` is an OAuth 2.0 **Desktop app** client secret downloaded from Google Cloud. Do not create this file manually from a password or API key.

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create a project, or select an existing project.
2. In **APIs & Services > Library**, enable:
   - **Gmail API**
   - **Google Sheets API**
3. In **APIs & Services > OAuth consent screen**, configure the consent screen:
   - Choose **External** unless the Google Workspace organization requires **Internal**.
   - Enter an application name and required contact information.
   - If the app is in **Testing** mode, add the Google account that will run the agent as a test user.
   - Add these scopes if the console asks you to select scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/spreadsheets`
4. Go to **APIs & Services > Credentials** and select **Create credentials > OAuth client ID**.
5. Choose **Desktop app**, enter a name, and select **Create**.
6. Download the client JSON file, rename it to `credentials.json`, and place it in the project root next to `authentication.py`.

The application requests these scopes on its first run:

- Gmail read-only access, to read messages from the inbox.
- Google Sheets access, to read and update application rows.

The first run opens a browser for consent and creates `token.json`. Keep both JSON files private. Never commit or publish them. If a token is revoked, delete `token.json` and run the agent again to authorize a new token.

## Configure the Google Sheet

The current code uses the spreadsheet ID configured in `sheets.py` and the worksheet tab named `Applications`. Create or share that spreadsheet with the Google account used during OAuth, and create a tab named `Applications`.

The expected columns are:

| ID | Date | Company Name | Role Name | Status |
| --- | --- | --- | --- | --- |

The application writes the statuses `applied`, `rejected`, and `proceeded`.

If you use a different spreadsheet, update `SPREADSHEET_ID` in `sheets.py`. If you use a different worksheet tab, update `SHEET_NAME` as well.

## Run the agent

With the virtual environment active, the Google OAuth client configured, the sheet ready, and Ollama running:

```bash
python agent.py
```

On the first run, complete the Google consent flow in the browser. Later runs reuse `token.json` and only refresh it when necessary.

Each run:

1. Reads up to 50 messages from the Gmail inbox.
2. Skips configured senders and message IDs already recorded in `emails.db`.
3. Classifies remaining messages with `gemma3:12b`.
4. Adds confirmed applications to the sheet or updates matching applications as rejected.
5. Records each examined message ID in the local database.

## Local files and security

The following files are generated or contain sensitive data and should remain local:

- `credentials.json`: Google OAuth client secret
- `token.json`: authorized Google account token
- `emails.db`: processed Gmail message IDs

If these files are not already ignored in your local Git configuration, add them to `.gitignore` before committing. Revoke OAuth credentials in Google Cloud if either JSON credential file is accidentally exposed.

## Troubleshooting

- **`FileNotFoundError: credentials.json`**: download a Desktop app OAuth client JSON file and place it in the project root.
- **OAuth access blocked**: confirm the account is listed as a test user on the OAuth consent screen when the app is in Testing mode.
- **Google API permission errors**: confirm both APIs are enabled and the spreadsheet is accessible by the authorized account.
- **Ollama connection or model errors**: start Ollama and run `ollama pull gemma3:12b`.
- **Messages are not processed again**: remove the relevant rows from `emails.db` only if you intentionally want to reprocess them. Deleting the database reprocesses all messages seen by the agent.