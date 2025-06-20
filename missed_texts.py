import sqlite3
import os
from datetime import datetime

# Path to messages database
db_path = os.path.expanduser("~/Library/Messages/chat.db")

conn = None

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query recent messages with contact info
    cursor.execute("""
        SELECT 
            m.text,
            m.date,
            m.is_from_me,
            m.service,
            h.id as phone_number,
            m.is_read,
            c.display_name as chat_name
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.ROWID
        WHERE m.text IS NOT NULL AND m.text != ''
        ORDER BY m.date DESC
        LIMIT 20
    """)
    
    print("Recent Text Messages:")
    print("-" * 100)
    
    for row in cursor.fetchall():
        text, timestamp, is_from_me, service, phone_number, is_read, chat_name = row
        
        # Convert timestamp to readable date
        # Messages use a different epoch (Jan 1, 2001)
        if timestamp:
            date = datetime.fromtimestamp(timestamp / 1000000000 + 978307200)
        else:
            date = "Unknown"
        
        # Determine direction
        direction = "Sent" if is_from_me == 1 else "Received"
        
        # Determine read status
        read_status = "Read" if is_read == 1 else "Unread"
        
        # Use chat name or phone number
        contact = chat_name if chat_name else phone_number
        
        # Truncate long messages for display
        display_text = text[:50] + "..." if len(text) > 50 else text
        
        # Service type (iMessage, SMS, etc.)
        service_type = service if service else "Unknown"
        
        print(f"{date} | {direction:8} | {read_status:6} | {service_type:8} | {contact:15} | {display_text}")
        
except Exception as e:
    print(f"Error accessing messages: {e}")
finally:
    if conn:
        conn.close()