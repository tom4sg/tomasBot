import os
import pickle
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

TOKEN_PICKLE = 'token.pickle'

def get_credentials():
    creds = None

    # Load existing token if exists
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config({
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    return creds

# Fetch upcoming events from Calendar
def get_upcoming_events(max_results=5):
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    # Modern timezone-aware timestamp
    now = datetime.now(timezone.utc).isoformat()

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime',
    ).execute()

    events = events_result.get('items', [])
    return events

if __name__ == '__main__':
    events = get_upcoming_events()

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])