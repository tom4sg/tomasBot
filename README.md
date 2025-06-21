# tomasBot - text and call auto-Responder

TomasBot automatically responds to missed calls and texts when you're on Do Not Disturb, calling Google Calendar API and Claude to send personalized messages to a specified contact list.

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
ANTHROPIC_API_KEY=your_claude_api_key
```

### 3. Configure Whitelist
Edit `close_friends_whitelist.json`:
```json
{
  "phone_numbers": ["+1234567890", "+1987654321"]
}
```

### 4. Run
```bash
python scripts/main.py
```

## How It Works

1. iPhone Shortcuts sends Do Not Disturb status changes to `/webhook/dnd`
2. Checks call history and messages databases every second
3. Only proceeds with response to whitelisted numbers
4. Looks up your current Google Calendar event
5. Claude generates response with calendar info
6. Delivers message via iMessage

## API Endpoints

- `POST /webhook/dnd` - DND status updates
- `GET /status` - Bot status and current calendar event
- `GET /whitelist` - View whitelist
- `POST /whitelist/add` - Add phone number
- `POST /whitelist/remove` - Remove phone number

## File Structure

```
scripts/
├── main.py                 # Main bot application
└── manage_whitelist.py     # Whitelist management tool

close_friends_whitelist.json  # Close friends phone numbers
start_tomas_bot.sh           # Startup script
```

## iPhone Shortcuts Setup

Create a Shortcut that:
1. Detects DND status changes
2. Sends POST to `http://your-ip:5001/webhook/dnd`
3. Body: `{"dnd_enabled": true/false}`

## Demo

https://github.com/user-attachments/assets/db824647-97c3-48c1-bcc5-efe17354c044


