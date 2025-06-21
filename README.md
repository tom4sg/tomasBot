# tomasBot - DND Responder

TomasBot automatically responds to missed calls and texts when you're unavailable, using your Google Calendar and Claude AI to send personalized messages.

## Features

- **DND Detection**: Receives webhook notifications when Do Not Disturb mode changes
- **Missed Call/Text Monitoring**: Detects and responds to missed communications
- **Google Calendar Integration**: Uses current events to personalize responses
- **Claude AI**: Generates natural, contextual responses
- **Whitelist System**: Only responds to close friends

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

1. **DND Webhook**: iPhone Shortcuts sends status changes to `/webhook/dnd`
2. **Monitoring**: Bot checks call history and messages databases every second
3. **Whitelist Check**: Only processes communications from whitelisted numbers
4. **Calendar Check**: Looks up current Google Calendar event
5. **AI Response**: Claude generates personalized response
6. **Send**: Delivers message via iMessage

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

## Example Responses

- **With Calendar**: "Tomas is at the gym until 7:30pm EST - try calling then! - TomasBot"
- **No Event**: "Tomas is busy but will get back to you soon! - TomasBot"
