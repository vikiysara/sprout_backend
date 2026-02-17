import os
import asyncio
from dotenv import load_dotenv
from google import genai 

load_dotenv()

# --- CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_KEY")

if not GEMINI_KEY:
    # Fallback for local testing if you used numbered keys
    GEMINI_KEY = os.getenv("GEMINI_KEY_1")

if not GEMINI_KEY:
    print("❌ Error: GEMINI_KEY not found in .env file")

# Best models in order of preference
MODELS = [
    "gemini-2.0-flash",       # Fastest & Smartest
    "gemini-1.5-flash",       # High Stability
    "gemini-flash-latest",    # Fallback
]

# --- CORE GENERATION ---
async def generate_raw_response(prompt: str):
    """Hits the API. Returns raw text. Handles errors gracefully."""
    if not GEMINI_KEY: return None

    try:
        client = genai.Client(api_key=GEMINI_KEY)

        for model_name in MODELS:
            try:
                # Run in thread to prevent blocking the server
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "quota" in err:
                    print(f"⚠️ Quota hit on {model_name}. Trying next...")
                    continue
                else:
                    print(f"⚠️ Error on {model_name}: {err[:50]}")
                    continue
                    
    except Exception as e:
        print(f"❌ Critical Client Error: {e}")
    
    return None

# --- PERSONA WRAPPER ---
async def chat_with_plant(user_msg, sensors, profile):
    prompt = f"""
    You are a {profile.get('species', 'plant')} named {profile.get('name', 'Sprout')}.
    Current Vitals:
    - Moisture: {sensors.get('soil_moisture', 0)}%
    - Temp: {sensors.get('temperature', 0)}°C
    - Light: {sensors.get('light_level', 0)} lux
    
    User said: "{user_msg}"
    
    Reply in 1-2 short, witty sentences. First person POV.
    """
    return await generate_raw_response(prompt)
