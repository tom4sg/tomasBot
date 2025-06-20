# TomasBot - Automated Response System

TomasBot is an intelligent automated response system that monitors your Do Not Disturb status, detects missed calls and texts, and sends personalized responses based on your Google Calendar events using Claude AI for natural language generation.

## Features

- **DND Detection**: Receives webhook notifications when Do Not Disturb mode changes
- **Missed Call Monitoring**: Automatically detects missed calls and sends responses
- **Unread Text Monitoring**: Detects unread messages and sends automated replies
- **Google Calendar Integration**: Uses current calendar events to personalize responses
- **Claude AI Integration**: Generates natural, contextual responses using Anthropic's Claude
- **Close Friends Whitelist**: Only sends automated responses to selected close friends

## How It Works

1. **DND Webhook**: iPhone Shortcuts sends a webhook when DND status changes
2. **Continuous Monitoring**: TomasBot monitors call history and messages databases
3. **Whitelist Check**: Only processes missed calls/texts from whitelisted phone numbers
4. **Calendar Check**: When a missed call/text is detected, it checks your current Google Calendar event
5. **AI Response Generation**: Claude generates a natural, contextual response based on your calendar
6. **Automated Response**: Sends the AI-generated message via iMessage

## Example Responses (AI-Generated)

- **With Calendar Event**: "Hey! Tomas is at the gym until 7:30pm EST - try calling him then! - TomasBot"
- **With Location**: "Tomas is in a team meeting at Conference Room A until 3pm EST. Give him a ring after that! - TomasBot"
- **No Event**: "Tomas is tied up right now but will get back to you soon! - TomasBot"

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials
5. Download the credentials JSON file

### 3. Claude AI Setup

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Add it to your `.env` file

### 4. Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
ANTHROPIC_API_KEY=your_claude_api_key
PORT=5001
HOST=0.0.0.0
```

### 5. iPhone Shortcuts Setup

Create a Shortcut that:
1. Detects when Do Not Disturb changes
2. Sends a POST request to `http://your-computer-ip:5001/webhook/dnd`
3. Includes JSON body: `{"dnd_enabled": true/false}`

### 6. Manage Close Friends Whitelist

Before running TomasBot, add your close friends' phone numbers to the whitelist:

```bash
python scripts/manage_whitelist.py
```

Or manually edit `close_friends_whitelist.json`:
```json
{
  "phone_numbers": [
    "+1234567890",
    "+1987654321"
  ],
  "description": "Phone numbers that should receive automated responses from TomasBot",
  "note": "Add phone numbers in international format (e.g., +1234567890)"
}
```

### 7. Run TomasBot

```bash
python scripts/main.py
```

Or use the startup script:
```bash
./start_tomas_bot.sh
```

## AI Response Generation

### Claude Integration

TomasBot uses Claude AI to generate natural, contextual responses:

- **System Prompt**: Defines TomasBot's personality and response style
- **Context-Aware**: Uses calendar event details when available
- **Natural Language**: Generates conversational, friendly responses
- **Fallback System**: Uses predefined messages if Claude is unavailable

### Response Customization

You can customize the AI responses by modifying the system message in `format_response_message()`:

```python
system_message = """You are TomasBot, an automated assistant that sends brief, friendly responses when Tomas is unavailable. 

Your responses should be:
- Brief and conversational (1-2 sentences max)
- Friendly and helpful
- Include Tomas's current activity if available
- Suggest when they should try calling again based on the end time of the event
- End with "- TomasBot"

If Tomas has a calendar event, mention what he's doing and when he'll be available.
If no calendar event is available, simply say he's busy and will get back to them soon.

Keep it formal and professional."""
```

### AI Model Configuration

- **Model**: `claude-3-5-sonnet-20240620` (powerful and capable)
- **Max Tokens**: 100 (keeps responses brief)
- **Temperature**: 0.7 (balanced creativity and consistency)

## Whitelist Management

### Using the Management Script

```bash
python scripts/manage_whitelist.py
```

This interactive script allows you to:
- View current whitelist
- Add phone numbers
- Remove phone numbers
- Edit whitelist in text editor

### API Endpoints for Whitelist

- `GET /whitelist` - Get current whitelist
- `POST /whitelist/add` - Add phone number to whitelist
- `POST /whitelist/remove` - Remove phone number from whitelist

Example API usage:
```bash
# Add a phone number
curl -X POST http://localhost:5001/whitelist/add \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "name": "John Doe"}'

# View whitelist
curl http://localhost:5001/whitelist
```

## API Endpoints

- `POST /webhook/dnd` - Receive DND status updates
- `GET /status` - Get current bot status and calendar event
- `GET /whitelist` - Get current whitelist
- `POST /whitelist/add` - Add phone number to whitelist
- `POST /whitelist/remove` - Remove phone number from whitelist
- `GET /test` - Test if the server is running

## File Structure

```
scripts/
├── main.py                 # Main integrated bot with Claude AI
├── manage_whitelist.py     # Whitelist management tool
├── test_claude.py          # Claude integration test
├── missed_calls.py         # Call history monitoring (legacy)
├── missed_texts.py         # Message monitoring (legacy)
├── google_calendar.py      # Calendar integration (legacy)
├── send_text.py            # iMessage sending (legacy)
└── is_busy.py             # Busy status detection (legacy)

close_friends_whitelist.json  # Whitelist of close friends
start_tomas_bot.sh           # Startup script
```

## Configuration

### Response Customization

Edit the system message in `format_response_message()` to customize AI response style and tone.

### Monitoring Frequency

Adjust the sleep time in `monitor_communications()` to change how often the system checks for missed calls/texts (default: 30 seconds).

### Calendar Event Window

Modify the time window in `get_current_calendar_event()` to change how far in advance/behind the system looks for calendar events.

### AI Model Settings

Customize Claude parameters in `format_response_message()`:
- `model`: Choose different Claude models
- `max_tokens`: Control response length
- `temperature`: Adjust creativity vs consistency

### Whitelist Behavior

- Only whitelisted phone numbers receive automated responses
- Non-whitelisted numbers are logged but ignored
- Phone numbers are normalized for comparison (e.g., "+1 (234) 567-8900" becomes "+12345678900")

## Troubleshooting

### Permission Issues
- Ensure the script has access to call history and messages databases
- Grant necessary permissions to Terminal/script editor

### Google Calendar Issues
- Verify OAuth credentials are correct
- Check that Calendar API is enabled
- Ensure token.pickle file is generated

### Claude AI Issues
- Verify ANTHROPIC_API_KEY is set correctly
- Check API key permissions and quota
- Ensure internet connection for API calls
- System will fallback to predefined messages if Claude fails

### iMessage Issues
- Make sure Messages app is signed in with your Apple ID
- Verify the recipient format (phone number or email)

### Whitelist Issues
- Ensure phone numbers are in international format (+1234567890)
- Check that the whitelist file exists and is valid JSON
- Use the management script to verify whitelist contents

## Logging

TomasBot creates detailed logs in `tomas_bot.log` including:
- DND status changes
- Missed call/text detection (whitelisted and non-whitelisted)
- AI response generation attempts
- Response sending attempts
- Calendar event queries
- Whitelist operations
- Error messages

## Cost Considerations

### Claude API Usage

- **Model**: claude-3-5-sonnet-20240620 (powerful option)
- **Cost**: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- **Typical Usage**: ~50-100 tokens per response
- **Estimated Cost**: <$5/month for typical usage

### Optimization Tips

- Use `max_tokens=100` to limit response length
- Monitor API usage in Anthropic console
- Consider caching responses for similar scenarios

## Security Notes

- The webhook endpoint should be secured in production
- Google Calendar credentials should be kept secure
- Claude API key should be kept secure
- Consider using HTTPS for webhook endpoints
- Database access requires appropriate permissions
- Whitelist file contains personal contact information - keep secure

## Development

To extend TomasBot:
1. Add new monitoring methods to the `TomasBot` class
2. Implement custom AI prompt logic in `format_response_message()`
3. Add new API endpoints in `setup_routes()`
4. Update the monitoring loop in `monitor_communications()`
5. Extend whitelist functionality as needed
6. Customize Claude system prompts for different scenarios

## License

This project is for personal use. Please respect privacy and security considerations when deploying.