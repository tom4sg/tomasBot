from flask import Flask, request, jsonify
from upcoming_events import is_busy, get_calendar_timezone
from sms import generate_sms, send_sms

app = Flask(__name__)

@app.route('/dnd-trigger', methods=['POST'])
def dnd_trigger():
    data = request.json
    print(f"DND Triggered: {data}")

    busy_status = is_busy()

    if busy_status['busy']:
        summary = busy_status['summary']
        end_dt = busy_status['end']

        calendar_tz = get_calendar_timezone()
        sms_text = generate_sms(summary, end_dt, calendar_tz)

        send_sms("+1YOUR_PHONE_NUMBER", sms_text)
        return jsonify({"message": "SMS sent"})

    else:
        print("No active event, no SMS sent.")
        return jsonify({"message": "Not busy"})

if __name__ == '__main__':
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)