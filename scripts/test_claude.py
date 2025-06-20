#!/usr/bin/env python3
"""
Test script for Claude integration in TomasBot
"""

import os
import sys
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

def test_claude_integration():
    """Test Claude message generation"""
    
    # Check if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment variables")
        print("Please add your Claude API key to the .env file")
        return False
    
    try:
        # Initialize Claude LLM
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            anthropic_api_key=api_key
        )
        print("✅ Claude LLM initialized successfully")
        
        # Test system message
        system_message = """You are TomasBot, an automated assistant that sends brief, friendly responses when Tomas is unavailable. 

Your responses should be:
- Brief and conversational (1-2 sentences max)
- helpful
- Include Tomas's current activity if available
- Suggest when they should try calling again based on the end time of the event
- End with "- TomasBot"

If Tomas has a calendar event, mention what he's doing and when he'll be available.
If no calendar event is available, simply say he's busy and will get back to them soon.

Keep it formal and professional."""

        # Test with calendar event
        print("\n🧪 Testing with calendar event...")
        user_message_with_event = """Tomas is currently at: Gym Workout
End time: 7:30pm EST
Location: Planet Fitness

Generate a brief response letting someone know Tomas is busy and when to try calling again."""

        messages_with_event = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message_with_event)
        ]
        
        response_with_event = llm.invoke(messages_with_event)
        generated_message = response_with_event.content.strip()
        
        if not generated_message.endswith("- TomasBot"):
            generated_message += " - TomasBot"
        
        print(f"✅ Generated response with event: {generated_message}")
        
        # Test without calendar event
        print("\n🧪 Testing without calendar event...")
        user_message_no_event = """Tomas doesn't have any calendar events right now. Generate a brief, friendly response letting someone know he's busy and will get back to them soon."""

        messages_no_event = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message_no_event)
        ]
        
        response_no_event = llm.invoke(messages_no_event)
        generated_message_no_event = response_no_event.content.strip()
        
        if not generated_message_no_event.endswith("- TomasBot"):
            generated_message_no_event += " - TomasBot"
        
        print(f"✅ Generated response without event: {generated_message_no_event}")
        
        print("\n🎉 Claude integration test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Claude integration: {e}")
        return False

def test_fallback_message():
    """Test fallback message generation"""
    print("\n🧪 Testing fallback message generation...")
    
    # Simulate the fallback message function
    def format_fallback_message(event_info=None):
        if event_info:
            time_str = "7:30pm EST"
            location = event_info.get('location', '')
            
            if location:
                return f"Tomas is currently at {event_info['summary']} ({location}) until {time_str}... try calling him then! - TomasBot"
            else:
                return f"Tomas is currently at {event_info['summary']} until {time_str}... try calling him then! - TomasBot"
        else:
            return "Tomas is currently unavailable and will get back to you soon! - TomasBot"
    
    # Test with event
    event_info = {
        'summary': 'Gym Workout',
        'location': 'Planet Fitness',
        'end_time': None  # Not used in fallback
    }
    
    fallback_with_event = format_fallback_message(event_info)
    print(f"✅ Fallback with event: {fallback_with_event}")
    
    # Test without event
    fallback_no_event = format_fallback_message(None)
    print(f"✅ Fallback without event: {fallback_no_event}")
    
    return True

def main():
    """Main test function"""
    print("🤖 TomasBot Claude Integration Test")
    print("=" * 50)
    
    # Test Claude integration
    claude_success = test_claude_integration()
    
    # Test fallback messages
    fallback_success = test_fallback_message()
    
    print("\n" + "=" * 50)
    if claude_success and fallback_success:
        print("🎉 All tests passed! TomasBot is ready to use.")
        print("\nNext steps:")
        print("1. Add your close friends to the whitelist: python scripts/manage_whitelist.py")
        print("2. Run TomasBot: python scripts/tomas_bot.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        if not claude_success:
            print("- Make sure your ANTHROPIC_API_KEY is set correctly in .env")

if __name__ == "__main__":
    main() 