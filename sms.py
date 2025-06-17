from datetime import timezone
from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load env variables once when the module is imported
load_dotenv()

# SMS Generator
def generate_sms(summary, end_dt, calendar_tz):
    """
    Generates a simple SMS message based on the event summary and end time.
    
    Args:
        summary (str): Event summary from Google Calendar
        end_dt (datetime): Event end time as a datetime object
        calendar_tz (tzinfo): The timezone object for formatting

    Returns:
        str: The message to be sent via SMS
    """
    end_time_local = end_dt.astimezone(calendar_tz)
    end_time_str = end_time_local.strftime("%I:%M %p %Z")

    sms = f"Tomas is currently busy with '{summary}' until {end_time_str}. Try calling him then."
    return sms

# Twilio SMS Sender
def send_sms(to_number, message_body):
    """
    Sends an SMS using Twilio API.

    Args:
        to_number (str): Destination phone number (E.164 format)
        message_body (str): Text message to send
    """
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=message_body,
        from_=from_number,
        to=to_number
    )

    print(f"SMS sent: {message.sid}")