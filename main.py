from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import uvicorn
import json
import random
import re
from contextlib import asynccontextmanager

# Import database functions
from database import (
    smart_log_data, get_recent_history, 
    save_plant_profile, get_plant_profile, get_weekly_analytics,
    get_raw_history_for_ai
)
# Import AI service
from ai_service import chat_with_plant 

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Sprout Pro Backend", lifespan=lifespan)

# --- MODELS ---
class SensorData(BaseModel):
    soil_moisture: int
    temperature: float
    humidity: int
    light_level: int

class ChatRequest(BaseModel):
    user_message: str
    current_sensors: dict 
    plant_name: str

class PlantNameRequest(BaseModel):
    plant_name: str

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Sprout Brain Online 🧠🌱"}

@app.post("/update_sensors")
async def update_sensors(data: SensorData):
    await smart_log_data(data.model_dump())
    return {"status": "Logged"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        profile = await get_plant_profile()
        profile['name'] = request.plant_name
        response = await chat_with_plant(request.user_message, request.current_sensors, profile)
        return {"reply": response if response else "I'm meditating... (API Quota)"}
    except:
        return {"reply": "My roots are crossed. Try again later."}

@app.get("/analytics/week")
async def get_weekly_stats():
    daily_stats = await get_weekly_analytics()
    
    if len(daily_stats) < 2:
        return {
            "daily_stats": [],
            "report_card": "Not enough data yet. I need at least 2 days to form an opinion! 🌱"
        }
        
    try:
        profile = await get_plant_profile()
        raw_logs = await get_raw_history_for_ai(days=7)
        
        prompt = f"""
        Analyze these 7 days of sensor logs for a {profile.get('name', 'Plant')}:
        {raw_logs}
        Write a 2-sentence weekly report card. Be helpful but slightly witty.
        """
        
        report_card = await chat_with_plant(prompt, {}, profile)
        if not report_card: raise Exception("Quota")
            
    except:
        avg = sum(d['avg_soil'] for d in daily_stats) / len(daily_stats)
        report_card = f"Weekly average moisture is {int(avg)}%. Looking stable."

    return {
        "daily_stats": daily_stats,
        "report_card": report_card
    }

# ... (Keep existing imports) ...

# --- 🚀 UPDATED DYNAMIC AI PLANT PROFILE ---
@app.post("/plant/care_profile")
async def get_care_profile(req: PlantNameRequest):
    print(f"🤖 Asking Gemini about: {req.plant_name}...")
    
    try:
        # 1. New "Plant POV" Prompt
        prompt = f"""
        Roleplay as a {req.plant_name}. Speak in the first person ("I", "me", "my").
        Return a valid JSON object with two keys:
        
        1. "tip": A funny, sassy, 1-sentence growing tip. Tell me what I need to stay healthy.
        2. "diseases": List 3 common diseases I get. Format as: "1. Disease Name (Prevention Tip)". Keep it short.
        
        Example Output:
        {{
            "tip": "Hey! I need my soil slightly moist, but don't drown my roots!",
            "diseases": "1. Root Rot (Let me drain)\\n2. Leaf Spot (Don't splash me)\\n3. Mites (Wipe my leaves)"
        }}
        
        Do not add Markdown. Just raw JSON.
        """

        # 2. Call Gemini
        response_text = await chat_with_plant(prompt, {}, {"name": req.plant_name})
        
        if not response_text: raise Exception("Empty Response")

        # 3. Clean JSON
        cleaned_text = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(cleaned_text)

    except Exception as e:
        print(f"❌ Profile Error: {e}")
        return {
            "tip": f"I'm a {req.plant_name}, and I love stable environments! (AI Offline)",
            "diseases": "1. Rot (Check water)\n2. Pests (Check leaves)\n3. Fungus (Airflow)"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)