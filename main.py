from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import json
import re
from contextlib import asynccontextmanager

# Import your modules
from database import (
    smart_log_data, get_weekly_analytics, 
    get_plant_profile, get_raw_history_for_ai
)
from ai_service import chat_with_plant, generate_raw_response 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌱 Sprout Backend Starting...")
    yield
    print("🍂 Sprout Backend Shutting Down...")

app = FastAPI(title="Sprout Pro Backend", lifespan=lifespan)

# --- DATA MODELS ---
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
    return {"status": "Online", "version": "1.0.0"}

@app.post("/update_sensors")
async def update_sensors(data: SensorData):
    # Just logs data. Returns success status.
    await smart_log_data(data.model_dump())
    return {"status": "Logged"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        profile = await get_plant_profile()
        profile['name'] = request.plant_name
        response = await chat_with_plant(request.user_message, request.current_sensors, profile)
        return {"reply": response if response else "I'm meditating... (API Quota)"}
    except Exception as e:
        print(f"Chat Error: {e}")
        return {"reply": "My roots are crossed. Try again later."}

@app.get("/analytics/week")
async def get_weekly_stats():
    daily_stats = await get_weekly_analytics()
    
    # Logic: If not enough data, give generic message
    if len(daily_stats) < 2:
        return {
            "daily_stats": daily_stats,
            "report_card": "Gathering more data... Keep me connected! 🌱"
        }
        
    try:
        profile = await get_plant_profile()
        raw_logs = await get_raw_history_for_ai(days=7)
        prompt = f"""
        Analyze these 7 days of sensor logs for a {profile.get('name', 'Plant')}:
        {raw_logs}
        Write a 2-sentence weekly report card. Be helpful but slightly witty.
        """
        report_card = await generate_raw_response(prompt)
        if not report_card: raise Exception("Quota")
    except:
        # Fallback if AI fails
        report_card = "Your plant is surviving! (AI Analysis Unavailable)"

    return {
        "daily_stats": daily_stats,
        "report_card": report_card
    }

@app.post("/plant/care_profile")
async def get_care_profile(req: PlantNameRequest):
    try:
        prompt = f"""
        Roleplay as a {req.plant_name}. 
        Return valid JSON with two keys:
        1. "tip": A funny 1-sentence growing tip (First person).
        2. "diseases": List 3 common diseases. Format: "1. Name (Prevention)".
        Do not add Markdown. Just raw JSON.
        """
        response_text = await generate_raw_response(prompt)
        if not response_text: raise Exception("Empty Response")

        # Clean JSON
        cleaned_text = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(cleaned_text)

    except Exception as e:
        print(f"Profile Error: {e}")
        return {
            "tip": f"I'm a {req.plant_name}, just keep me alive!",
            "diseases": "1. Rot (Check water)\n2. Pests (Look closely)\n3. Unknown (Google it)"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
