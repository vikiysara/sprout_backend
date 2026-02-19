from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json
import re
import logging
from contextlib import asynccontextmanager

from database import (
    smart_log_data,
    get_weekly_analytics,
    get_plant_profile,
    get_raw_history_for_ai
)

from ai_service import chat_with_plant, generate_raw_response

# =====================================================
# LOGGING & APP SETUP
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SproutBackend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌱 Sprout Pro v2.0: 6-Tier AI Fallback Strategy Active...")
    yield
    logger.info("🍂 Sprout Backend shutting down...")

app = FastAPI(title="Sprout Pro Backend v2.0", lifespan=lifespan)

# Mapping endpoints to your requested order
MODEL_TIERS = {
    "default": "gemini-2.5-flash-lite", # First choice
    "backup": "gemini-2.5-flash",       # Second choice
    "diagnostics": "gemini-2.5-pro"     # Final choice for complex health
}

# =====================================================
# REQUEST MODELS
# =====================================================

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

# =====================================================
# ENDPOINTS
# =====================================================

@app.get("/")
async def home():
    return {"status": "online", "priority_order": ["2.5 Flash Lite", "2.5 Flash", "2 Flash", "2 Flash Lite", "2 Flash Exp", "2.5 Pro"]}

@app.post("/update_sensors")
async def update_sensors(data: SensorData):
    await smart_log_data(data.model_dump())
    return {"status": "logged"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        profile = await get_plant_profile()
        profile["name"] = request.plant_name
        msg = request.user_message.lower()

        # Complex health questions go to the high-intelligence tier (Pro)
        is_medical = any(w in msg for w in ["dying", "sick", "help", "why", "brown", "yellow", "spots"])
        model = MODEL_TIERS["diagnostics"] if is_medical else MODEL_TIERS["default"]

        reply = await chat_with_plant(
            request.user_message,
            request.current_sensors,
            profile,
            model_name=model
        )

        return {"reply": reply, "engine": model}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": "My leaves are a bit tangled. Try again in a minute! 🌱", "engine": "error"}

@app.get("/analytics/week")
async def get_weekly_stats():
    daily_stats = await get_weekly_analytics()
    if len(daily_stats) < 2:
        return {"daily_stats": daily_stats, "report_card": "Just getting settled in! Check back later for my weekly update. 📡"}

    try:
        raw_logs = await get_raw_history_for_ai(days=7)
        profile = await get_plant_profile()

        prompt = f"""
        ROLE: You are a friendly, casual {profile.get('name','plant')}.
        CONTEXT: Look at your sensor logs from the past week: {raw_logs}
        
        TASK: Write a 2-sentence weekly update telling your friend (the user) how your week went.
        GUIDELINES: 
        1. Use very simple, everyday English.
        2. Be casual and friendly. 
        3. Do not sound robotic, and do not use big dictionary words.
        """

        # Start analysis with your top-priority model
        report = await generate_raw_response(prompt, model_name=MODEL_TIERS["default"])
        return {"daily_stats": daily_stats, "report_card": report or "I'm still thinking about my week!"}

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return {"daily_stats": daily_stats, "report_card": "Taking a quick nap, check my report later."}

@app.post("/plant/care_profile")
async def get_care_profile(req: PlantNameRequest):
    try:
        prompt = f"""
        ROLE: You are a friendly {req.plant_name}.
        TASK: Return strictly valid JSON with keys "tip" and "diseases".
        
        GUIDELINES:
        - "tip": Write 2 short, friendly sentences of everyday advice in the first person. Keep it super simple.
        - "diseases": List 3 common issues formatted simply (e.g., "1. Bug name (How to fix)").
        
        CONSTRAINT: Return ONLY raw JSON. No Markdown. No big dictionary words.
        """
        text = await generate_raw_response(prompt, model_name=MODEL_TIERS["default"])
        match = re.search(r'\{.*\}', text, re.DOTALL)
        json_str = match.group(0) if match else text.strip()
        return json.loads(json_str)

    except Exception as e:
        logger.error(f"Care profile error: {e}")
        return {
            "tip": f"Hey, I'm a {req.plant_name}! Just make sure to check my soil before watering me.",
            "diseases": "1. Root Rot (let me dry out) 2. Pests (wipe my leaves) 3. Sunburn (move me to the shade)"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
