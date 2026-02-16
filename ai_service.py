import os
import google.generativeai as genai
from dotenv import load_dotenv
import random
import asyncio

load_dotenv()

# --- 1. LOAD ALL KEYS ---
# We look for keys named GEMINI_KEY_1, GEMINI_KEY_2, etc.
API_KEYS = []
i = 1
while True:
    key = os.getenv(f"GEMINI_KEY_{i}")
    if not key: break
    API_KEYS.append(key)
    i += 1

if not API_KEYS:
    # Fallback to standard name if numbered ones aren't found
    single_key = os.getenv("GOOGLE_API_KEY")
    if single_key: API_KEYS.append(single_key)

print(f"🔑 Loaded {len(API_KEYS)} Gemini API Keys.")

# --- 2. FAILOVER FUNCTION ---
async def safe_generate_content(prompt: str):
    """
    Tries keys one by one. If Key 1 fails (Quota), it switches to Key 2.
    """
    # Shuffle keys so we don't always hammer Key 1 first
    # (Optional: remove shuffle if you want a strict order)
    shuffled_keys = API_KEYS.copy()
    random.shuffle(shuffled_keys)

    for key in shuffled_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Run in executor because genai is synchronous
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            print(f"⚠️ Key failed: {str(e)[:50]}... Trying next key.")
            continue
            
    print("❌ All Gemini Keys exhausted.")
    return None

# --- 3. EXPORTED FUNCTIONS ---

async def chat_with_plant(user_msg, sensors, profile):
    prompt = f"""
    You are a {profile.get('species', 'plant')} named {profile.get('name', 'Sprout')}.
    
    Current Vitals:
    - Moisture: {sensors.get('soil_moisture', 0)}%
    - Temp: {sensors.get('temperature', 0)}°C
    - Light: {sensors.get('light_level', 0)} lux
    
    User said: "{user_msg}"
    
    Reply in 1-2 short, funny sentences. First person.
    """
    return await safe_generate_content(prompt)

async def get_botanist_analysis(sensors, history, profile):
    # (This function might not be used in your current flow, but keeping it safe)
    return "Analysis complete." 

async def generate_weekly_report(daily_stats, profile):
    # This is handled dynamically in main.py now, but keeping placeholder
    return "Weekly report ready."

async def analyze_plant_image(image_bytes, sensors):
    # (Placeholder if you add image features later)
    return "Image analyzed."

async def get_common_diseases(profile):
    # (Placeholder)
    return "Root rot, Pests."