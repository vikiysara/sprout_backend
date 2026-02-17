from fastapi import FastAPI
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
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SproutBackend")

# =====================================================
# APP LIFECYCLE
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌱 Sprout Backend starting...")
    yield
    logger.info("🍂 Sprout Backend shutting down...")

app = FastAPI(title="Sprout Pro Backend v2.0", lifespan=lifespan)

# =====================================================
# MODEL TIERS (only working ones)
# =====================================================

MODEL_TIERS = {
    "smart": "gemini-2.5-flash",        # default
    "analysis": "gemini-2.5-flash",     # heavy reasoning
    "lite": "gemini-2.5-flash-lite"     # cheap fallback
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
# ROOT
# =====================================================

@app.get("/")
async def home():
    return {
        "status": "online",
        "version": "2.0.0",
        "models": MODEL_TIERS
    }


# =====================================================
# SENSOR LOGGING
# =====================================================

@app.post("/update_sensors")
async def update_sensors(data: SensorData):
    await smart_log_data(data.model_dump())
    return {"status": "logged"}


# =====================================================
# CHAT ENDPOINT
# =====================================================

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        profile = await get_plant_profile()
        profile["name"] = request.plant_name

        msg = request.user_message.lower()

        # smarter routing
        needs_analysis = any(
            word in msg
            for word in ["dying", "sick", "help", "why", "brown", "yellow"]
        )

        model = (
            MODEL_TIERS["analysis"]
            if needs_analysis
            else MODEL_TIERS["smart"]
        )

        reply = await chat_with_plant(
            request.user_message,
            request.current_sensors,
            profile,
            model_name=model
        )

        if not reply:
            reply = await chat_with_plant(
                request.user_message,
                request.current_sensors,
                profile,
                model_name=MODEL_TIERS["lite"]
            )
            model = "fallback-lite"

        return {"reply": reply, "engine": model}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "reply": "My neural roots are tangled. Try again soon 🌱",
            "engine": "error"
        }


# =====================================================
# WEEKLY ANALYTICS
# =====================================================

@app.get("/analytics/week")
async def get_weekly_stats():
    daily_stats = await get_weekly_analytics()

    if len(daily_stats) < 2:
        return {
            "daily_stats": daily_stats,
            "report_card": "Collecting more biological data 🌱"
        }

    try:
        raw_logs = await get_raw_history_for_ai(days=7)
        profile = await get_plant_profile()

        prompt = f"""
You are a plant bio-analyst.

Plant: {profile.get('name','plant')}
Data: {raw_logs}

1. Find stress point of week.
2. Give 2 sentence witty report card.
"""

        report = await generate_raw_response(
            prompt,
            model_name=MODEL_TIERS["lite"]
        )

        return {
            "daily_stats": daily_stats,
            "report_card": report or "Analysis pending"
        }

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return {
            "daily_stats": daily_stats,
            "report_card": "Analysis pending"
        }


# =====================================================
# CARE PROFILE
# =====================================================

@app.post("/plant/care_profile")
async def get_care_profile(req: PlantNameRequest):
    try:
        prompt = f"""
Roleplay as {req.plant_name}.
Return strictly valid JSON:

{{
"tip":"1 sentence first person tip",
"diseases":"3 diseases with prevention"
}}
"""

        text = await generate_raw_response(
            prompt,
            model_name=MODEL_TIERS["lite"]
        )

        if not text:
            raise ValueError("empty response")

        cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
        return json.loads(cleaned)

    except Exception as e:
        logger.error(f"Care profile error: {e}")
        return {
            "tip": f"I'm a {req.plant_name}, keep my soil moist 🌱",
            "diseases": "Root Rot (avoid overwatering)"
        }


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
