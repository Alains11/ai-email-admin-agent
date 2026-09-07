"""Interactive terminal client for the chat API."""

import asyncio
import requests

async def main():
    print("--- AI Email Admin Agent CLI ---")
    print("Type 'exit' or 'quit' to stop.")
    
    # Configuration
    API_URL = "http://127.0.0.1:8000/api/v1/chat"
    provider = input("Enter email provider (gmail/yahoo/outlook) [yahoo]: ") or "yahoo"
    session_id = input("Enter session ID [default]: ") or "default"
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        payload = {
            "message": user_input,
            "provider": provider,
            "credentials": {},
            "session_id": session_id
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"\nAI: {data.get('response', 'No response received.')}")
            else:
                print(f"\nError: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to the server. Is the FastAPI app running?")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
