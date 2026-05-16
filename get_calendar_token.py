"""
One-time script: obtain OAuth2 token for Google Calendar.

Usage:
    pip install google-auth-oauthlib
    python get_calendar_token.py

A browser window will open. Log in as bot@amiga-migrant.cz
(NOT your personal account).

On success, token.json is written to the current directory and
its contents are printed — paste the printed JSON as the value
of GOOGLE_CALENDAR_TOKEN_JSON in Render environment variables.
"""

import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def main() -> None:
    print("Starting OAuth2 flow...")
    print(">>> IMPORTANT: log in as bot@amiga-migrant.cz <<<\n")

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = json.loads(creds.to_json())

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nSaved to {TOKEN_FILE}")
    print("\n=== Paste this as GOOGLE_CALENDAR_TOKEN_JSON in Render ===\n")
    print(json.dumps(token_data))
    print("\n==========================================================")
    print("Done. Keep token.json secret — never commit it to git.")


if __name__ == "__main__":
    main()
