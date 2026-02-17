import os
import asyncio
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger("AIService")

# =====================================================
# CONFIG
# =====================================================

GEMINI_KEY = os.getenv("GEMINI_KEY") or os.getenv("GEMINI_KEY_1")

if not GEMINI_KEY:
    raise RuntimeError("❌ GEMINI_KEY missing")

client = genai.Client(api_key=GEMINI_KEY)

# working models only
MODEL_PRIORITY = [
    "gemini-2.5-flash",        # main
    "gemini-2.5-flash-exp",    # backup
    "gemini-2.5-flash-lite",   # final fallback
]

REQUEST_TIMEOUT = 15
MAX_RETRIES = 2


# =====================================================
# LOW LEVEL CALL
# =====================================================

async def _call_model(model: str, prompt: str):
    return await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=prompt
        ),
        timeout=REQUEST_TIMEOUT
    )


# =====================================================
# SMART GENERATION ENGINE
# =====================================================

async def generate_raw_response(prompt: str, model_name=None):
    """
    Smart routing with retry + fallback.
    """

    models = []

    if model_name:
        models.append(model_name)

    models.extend(m for m in MODEL_PRIORITY if m not in models)

    for model in models:

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"⚡ {model} attempt {attempt+1}")

                res = await _call_model(model, prompt)

                if res and res.text:
                    return res.text.strip()

            except asyncio.TimeoutError:
                logger.warning(f"Timeout → {model}")

            except Exception as e:
                err = str(e).lower()

                if "429" in err or "quota" in err:
                    logger.warning(f"Quota hit → {model}")
                    break

                if "404" in err or "not found" in err:
                    logger.warning(f"Model unavailable → {model}")
                    break

                logger.error(f"{model}: {err[:100]}")

            # exponential backoff
            await asyncio.sleep(1.5 ** attempt)

    logger.error("❌ All models failed")
    return None


# =====================================================
# PLANT CHAT
# =====================================================

async def chat_with_plant(
    user_msg,
    sensors,
    profile,
    model_name=None
):
    prompt = f"""
You are a {profile.get('species','plant')} named {profile.get('name','Sprout')}.

Vitals:
Moisture: {sensors.get('soil_moisture',0)}%
Temperature: {sensors.get('temperature',0)}°C
Light: {sensors.get('light_level',0)} lux

User: "{user_msg}"

Reply in 1-2 witty sentences in first person.
"""

    return await generate_raw_response(prompt, model_name)
