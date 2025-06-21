#!/usr/bin/env python3
"""
Whitelist Management Script for TomasBot
Helps manage the list of close friends who should receive automated responses.
"""

import json
import os
import sys

WHITELIST_FILE = 'close_friends_whitelist.json'

def load_whitelist():
    """Load the current whitelist"""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r') as f:
            data = json.load(f)
            return data.get('phone_numbers', [])
    return []

def save_whitelist(phone_numbers):
    """Save the whitelist to file"""
    data = {
        "phone_numbers": phone_numbers,
        "description": "Phone numbers that should receive automated responses from TomasBot",
        "note": "Add phone numbers in international format (e.g., +1234567890)"
    }
    
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def normalize_phone_number(phone_number):
    """Normalize phone number for comparison"""
    if not phone_number:
        return ""
    
    # Remove all non-digit characters except +
    normalized = ''.join(c for c in phone_number if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not normalized.startswith('+'):
        normalized = '+' + normalized
    
    return normalized

def add_number():
    """Add a phone number to the whitelist"""
    phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
    name = input("Enter contact name (optional): ").strip()
    
    if not phone_number:
        print("Phone number is required!")
        return
    
    normalized_number = normalize_phone_number(phone_number)
    whitelist = load_whitelist()
    
    if normalized_number in whitelist:
        print(f"{normalized_number} is already in the whitelist")
    else:
        whitelist.append(normalized_number)
        save_whitelist(whitelist)
        print(f"Added {normalized_number} ({name}) to whitelist")

def remove_number():
    """Remove a phone number from the whitelist"""
    whitelist = load_whitelist()
    
    if not whitelist:
        print("Whitelist is empty!")
        return
    
    print("\nCurrent whitelist:")
    for i, number in enumerate(whitelist, 1):
        print(f"{i}. {number}")
    
    try:
        choice = int(input("\nEnter number to remove (1, 2, 3...): ")) - 1
        if 0 <= choice < len(whitelist):
            removed_number = whitelist.pop(choice)
            save_whitelist(whitelist)
            print(f"Removed {removed_number} from whitelist")
        else:
            print("Invalid choice!")
    except ValueError:
        print("Please enter a valid number!")

def view_whitelist():
    """View the current whitelist"""
    whitelist = load_whitelist()
    
    if not whitelist:
        print("Whitelist is empty")
        print("Add phone numbers to start receiving automated responses from TomasBot")
    else:
        print(f"Current whitelist ({len(whitelist)} contacts):")
        print("-" * 40)
        for i, number in enumerate(whitelist, 1):
            print(f"{i}. {number}")
        print("-" * 40)

def edit_whitelist():
    """Edit the whitelist directly in a text editor"""
    whitelist = load_whitelist()
    
    print("Opening whitelist file for editing...")
    print("Format: One phone number per line, international format (e.g., +1234567890)")
    
    # Create a temporary file with current numbers
    temp_content = "\n".join(whitelist) if whitelist else "# Add phone numbers here (one per line)\n# Example: +1234567890"
    
    temp_file = f"{WHITELIST_FILE}.tmp"
    with open(temp_file, 'w') as f:
        f.write(temp_content)
    
    # Open in default editor
    editor = os.environ.get('EDITOR', 'nano')
    os.system(f"{editor} {temp_file}")
    
    # Read back the edited file
    try:
        with open(temp_file, 'r') as f:
            lines = f.readlines()
        
        # Parse phone numbers (skip comments and empty lines)
        new_numbers = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                normalized = normalize_phone_number(line)
                if normalized:
                    new_numbers.append(normalized)
        
        save_whitelist(new_numbers)
        print(f"Updated whitelist with {len(new_numbers)} phone numbers")
        
    except Exception as e:
        print(f"Error reading edited file: {e}")
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)

def main():
    """Main menu"""
    while True:
        print("\n" + "="*50)
        print("TomasBot Whitelist Manager")
        print("="*50)
        print("1. View current whitelist")
        print("2. Add phone number")
        print("3. Remove phone number")
        print("4. Edit whitelist (text editor)")
        print("5. Exit")
        print("-"*50)
        
        choice = input("Choose an option (1-5): ").strip()
        
        if choice == '1':
            view_whitelist()
        elif choice == '2':
            add_number()
        elif choice == '3':
            remove_number()
        elif choice == '4':
            edit_whitelist()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice! Please enter 1-5")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 