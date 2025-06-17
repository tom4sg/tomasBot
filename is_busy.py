import os
import pickle
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz

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

def get_calendar_timezone():
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)
    calendar = service.calendars().get(calendarId='primary').execute()
    calendar_timezone = calendar['timeZone']
    return pytz.timezone(calendar_timezone)

def is_busy():
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    # Get current time in calendar's timezone
    tz = get_calendar_timezone()
    now = datetime.now(tz)
    now_iso = now.isoformat()

    # Query events starting from now and going slightly backwards to catch overlapping events
    events_result = service.events().list(
        calendarId='primary',
        timeMin=(now - timedelta(minutes=5)).isoformat(),  # allow for slight clock mismatches
        timeMax=(now + timedelta(minutes=1)).isoformat(),  # check if something just started
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # Look for any events that overlap with current time
    for event in events:
        start_str = event['start'].get('dateTime')
        end_str = event['end'].get('dateTime')

        if start_str and end_str:
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)

            if start <= now <= end:
                # You are currently busy
                return {
                    "busy": True,
                    "summary": event['summary'],
                    "start": start,
                    "end": end
                }

    # No event found that overlaps with now
    return { "busy": False }

if __name__ == '__main__':
    print(is_busy())