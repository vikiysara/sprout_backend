import os
import google.generativeai as genai
from dotenv import load_dotenv
import random
import asyncio

load_dotenv()

# --- 1. LOAD ALL KEYS ---
API_KEYS = []
i = 1
while True:
    key = os.getenv(f"GEMINI_KEY_{i}")
    if not key: break
    API_KEYS.append(key)
    i += 1

if not API_KEYS:
    single_key = os.getenv("GOOGLE_API_KEY")
    if single_key: API_KEYS.append(single_key)

print(f"🔑 Loaded {len(API_KEYS)} Gemini API Keys.")

# --- 2. FAILOVER FUNCTION ---
async def safe_generate_content(prompt: str):
    """
    Tries keys one by one. 
    Tries the specific models found in your logs.
    """
    shuffled_keys = API_KEYS.copy()
    random.shuffle(shuffled_keys)

    # ✅ UPDATED: Only using models confirmed in your logs
    model_names = [
        'gemini-2.0-flash',       # Fast & Stable
        'gemini-2.5-flash',       # Newest
        'gemini-flash-latest',    # Generic Fallback
        'gemini-pro'              # Legacy Fallback
    ]

    for key in shuffled_keys:
        try:
            genai.configure(api_key=key)
            
            for model_name in model_names:
                try:
                    # Create model
                    model = genai.GenerativeModel(model_name)
                    
                    # Run generation
                    response = await asyncio.to_thread(model.generate_content, prompt)
                    
                    if response and response.text:
                        print(f"✅ Success using Key ...{key[-4:]} with model {model_name}")
                        return response.text
                        
                except Exception as e:
                    error_str = str(e).lower()
                    # If model not found (404), try next model in list
                    if "404" in error_str or "not found" in error_str:
                        continue 
                    # If quota (429), stop this key loop and try next key
                    elif "429" in error_str or "quota" in error_str:
                        print(f"⚠️ Key ...{key[-4:]} Quota Exceeded. Switching keys...")
                        break 
                    else:
                        print(f"⚠️ Error with {model_name}: {e}")
                        continue
                
        except Exception as e:
            print(f"⚠️ Key Config Failed: {e}")
            continue
            
    print("❌ All Gemini Keys exhausted or no models worked.")
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
    return "Analysis placeholder"

async def generate_weekly_report(daily_stats, profile):
    return "Report placeholder"

async def analyze_plant_image(image_bytes, sensors):
    return "Image analyzed."

async def get_common_diseases(profile):
    return "Root rot, Pests."
