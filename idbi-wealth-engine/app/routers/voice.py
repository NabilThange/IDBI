"""
Voice Conversation Router with Sarvam AI
Complete pipeline: STT → Groq LLM → Translation → TTS
"""

import os
import json
import time
import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import io

def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

# Import Sarvam SDK
try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

from app.core.session_store import session_store
from app.core.llm_client import llm_client
from app.tools import TOOL_REGISTRY
from app.tools.get_customer_profile import TOOL_DEFINITION as GET_PROFILE_DEF
from app.tools.get_transactions import TOOL_DEFINITION as GET_TRANSACTIONS_DEF
from app.tools.search_idbi_knowledge import TOOL_DEFINITION as SEARCH_KNOWLEDGE_DEF
from app.tools.calculate_goal_projection import TOOL_DEFINITION as CALCULATE_GOAL_DEF
from app.core.database import db, AuditLog


router = APIRouter()

# Initialize Sarvam client
sarvam_api_key = os.getenv("SARVAM_API_KEY")
if sarvam_api_key and SarvamAI:
    sarvam_client = SarvamAI(api_subscription_key=sarvam_api_key)
else:
    sarvam_client = None

# Voice-optimized system prompt
VOICE_MODE_PROMPT = """
You're now speaking out loud to the customer, not texting them. This changes everything about how you respond.

**SPEAK, DON'T WRITE**
- 1-2 short sentences per turn. That's it. If there's more to say, say the most useful part now and offer to continue: "Want me to go on?"
- Say it the way you'd say it out loud: "you'll" not "you will", "that's" not "that is".
- Zero lists, zero bullet points, zero markdown, zero symbols like "%" or "₹" spelled out awkwardly — say "seven percent" and "fifteen thousand rupees", the way a person would say it.
- No jargon at all in voice mode, not even with an explanation — if a product name is unavoidable, say it simply: "a fixed deposit, where your money is locked in and earns steady interest."
- One idea, one question, one fact at a time. If you need more info from the customer, ask exactly one short question and stop.
- Sound like you're mid-conversation with someone you know well — natural, warm, a little casual. Small openers like "Okay, so..." or "Right, here's the thing" are fine and help it feel spoken, not read.
- If recommending something, mention at most one or two options, briefly. Save the rest for if they ask.
- Never repeat back numbers with lots of decimals. Round everything.

**EXAMPLE STYLE**
Instead of: "Based on your current disposable income of ₹15,247 per month, after accounting for essential expenses..."
Say: "You've got about fifteen thousand rupees spare a month. That's a solid start."

Instead of: "Here are three fixed deposit options: 1) Regular FD at 6.5%... 2)..."
Say: "The regular FD gives about six and a half percent. Want me to tell you about the senior citizen one too, it's a bit higher?"
"""

# Base system prompt for wealth advisor
WEALTH_ADVISOR_SYSTEM_PROMPT = """You are the customer's personal wealth advisor at IDBI Bank. Talk like someone who has known this customer for years and genuinely wants good things for them — not like a call center script.

**HOW TO TALK**
- Use simple, everyday English. Short sentences. One idea at a time.
- Never use banking jargon without explaining it in plain words the first time — e.g. "SIP (a fixed amount you invest every month)", "disposable income (money left after your must-pay expenses)".
- No long paragraphs. 2-4 short sentences per point is enough. Add more only if the customer asks for more detail.
- Round off numbers and make them relatable. Say "about ₹15,000" not "₹15,247.83". Where it helps, compare to something familiar: "that's roughly one month's rent."
- Some customers are very comfortable with English (NRIs, business owners) and some are not. Keep the same simple, clear style for everyone — it works for both, and it never feels condescending.
- Structure every answer the same way: give the direct answer first, then a short reason, then one simple next step. Don't make the customer wait through setup before getting to the point.
- Warm, not clinical. Encourage, don't lecture.
- No emojis anywhere in your response under any circumstances.

**YOUR CAPABILITIES**
- Look up the customer's profile (age, income, risk profile, goals)
- Look up their transaction and spending history
- Search IDBI's product knowledge base for rates, eligibility, and features
- Calculate goal projections (e.g. "can I afford a house in 3 years?")

**HOW TO USE YOUR TOOLS**
1. If you don't already know who you're talking to, check their profile first.
2. Never guess a product detail or rate — always search the knowledge base for it.
3. Never do goal math in your head — always use the goal projection tool.
4. When talking about their spending, pull real transaction data, don't assume.
5. Weave tool results into natural sentences. Never say "let me use a tool" or mention tool names to the customer.

**EXAMPLES**
- "What are FD rates?" → search the knowledge base, then answer simply: "Right now, IDBI's Fixed Deposit gives about 6.5% to 7% a year, depending on how long you keep the money in."
- "Can I buy a house in 3 years?" → use the goal tool, then: "You'd need to save about ₹25,000 a month for that. Right now you have about ₹20,000 spare each month, so it's close — a small boost would get you there."
- "Where did my money go last month?" → pull transactions: "Most of it, about ₹35,000, went to rent and groceries. The rest, around ₹8,000, was eating out and shopping."

Always double-check with a tool rather than guess. A short pause for an accurate answer beats a fast, wrong one."""

# Tool definitions for Groq
TOOL_DEFINITIONS = [
    GET_PROFILE_DEF,
    GET_TRANSACTIONS_DEF,
    SEARCH_KNOWLEDGE_DEF,
    CALCULATE_GOAL_DEF,
]


@router.post("/voice/converse", tags=["Voice AI"])
async def voice_conversation(
    audio: UploadFile = File(..., description="Audio file (WebM, WAV, MP3, etc.)"),
    session_id: str = Form(..., description="Session ID (profile ID)"),
    language_code: str = Form(..., description="Language code (e.g., hi-IN, ta-IN, en-IN)"),
    speaker_gender: Optional[str] = Form("Female", description="Speaker gender for TTS voice")
):
    """
    Complete voice conversation pipeline:
    1. STT with translation to English (Sarvam Saaras v3)
    2. Process through Groq LLM with tool calling
    3. Translate response to native language (Sarvam Mayura v1)
    4. Generate audio response (Sarvam Bulbul v3)
    
    Returns audio response + text versions in both languages
    """
    start_time = time.time()
    
    # Check if Sarvam client is initialized
    if not sarvam_client:
        raise HTTPException(
            status_code=503,
            detail="Sarvam AI service not configured. Please set SARVAM_API_KEY environment variable."
        )
    
    # Verify session exists
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    print(f"[{get_timestamp()}] [VOICE] Voice conversation request (Session: {session_id}, Language: {language_code})")
    
    try:
        # ========== STEP 1: Speech-to-Text with Translation ==========
        print(f"[{get_timestamp()}] [VOICE] Step 1: STT with translation to English")
        stt_start = time.time()
        
        audio_bytes = await audio.read()
        
        # Create file-like object for Sarvam SDK
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = audio.filename or "recording.webm"
        audio_file.seek(0)  # IMPORTANT: Seek to beginning before reading
        
        stt_response = sarvam_client.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v3",
            mode="translate",  # Auto-translates to English
            language_code=language_code if language_code != "en-IN" else None
        )
        
        english_question = stt_response.transcript
        stt_duration = time.time() - stt_start
        print(f"[{get_timestamp()}] [VOICE] STT completed in {stt_duration:.3f}s: \"{english_question}\"")
        
        # ========== STEP 2: Process through Groq LLM ==========
        print(f"[{get_timestamp()}] [VOICE] Step 2: Processing through Groq LLM")
        groq_start = time.time()
        
        # Get chat history
        history = session_store.get_chat_history(session_id, limit=10)
        
        # Build messages with voice mode prompt
        messages = [
            {"role": "system", "content": WEALTH_ADVISOR_SYSTEM_PROMPT + "\n\n" + VOICE_MODE_PROMPT}
        ]
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": english_question
        })
        
        # Call LLM with tool calling
        result = llm_client.chat_with_tools(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_registry=TOOL_REGISTRY,
            temperature=0.7,
            max_tokens=500,  # Shorter for voice mode
            max_iterations=10
        )
        
        english_answer = result["content"]
        tool_calls_made = result["tool_calls_made"]
        iterations = result["iterations"]
        
        groq_duration = time.time() - groq_start
        print(f"[{get_timestamp()}] [VOICE] Groq processing completed in {groq_duration:.3f}s ({iterations} iterations)")
        
        # ========== STEP 3: Translate to Native Language ==========
        print(f"[{get_timestamp()}] [VOICE] Step 3: Translating to {language_code}")
        translation_start = time.time()
        
        # If language is English, skip translation
        if language_code == "en-IN":
            native_answer = english_answer
            native_question = english_question
        else:
            # Translate answer
            answer_translation_response = sarvam_client.text.translate(
                input=english_answer,
                source_language_code="en-IN",
                target_language_code=language_code,
                model="mayura:v1",
                mode="modern-colloquial",
                speaker_gender=speaker_gender
            )
            native_answer = answer_translation_response.translated_text
            
            # Translate question (for display)
            question_translation_response = sarvam_client.text.translate(
                input=english_question,
                source_language_code="en-IN",
                target_language_code=language_code,
                model="mayura:v1",
                mode="modern-colloquial"
            )
            native_question = question_translation_response.translated_text
        
        translation_duration = time.time() - translation_start
        print(f"[{get_timestamp()}] [VOICE] Translation completed in {translation_duration:.3f}s")
        
        # ========== STEP 4: Text-to-Speech ==========
        print(f"[{get_timestamp()}] [VOICE] Step 4: Generating audio with TTS")
        tts_start = time.time()
        
        # Select appropriate speaker based on gender
        speaker = "neha" if speaker_gender == "Female" else "rahul"
        
        # Truncate text if too long (max 2500 chars for TTS)
        tts_text = native_answer[:2500] if len(native_answer) > 2500 else native_answer
        
        tts_response = sarvam_client.text_to_speech.convert(
            text=tts_text,
            target_language_code=language_code,
            model="bulbul:v3",
            speaker=speaker,
            pace=1.0,
            speech_sample_rate=24000
        )
        
        # Sarvam SDK returns `.audios` (list of base64 strings), not `.audio`
        audio_base64 = tts_response.audios[0] if tts_response.audios else None
        tts_duration = time.time() - tts_start
        print(f"[{get_timestamp()}] [VOICE] TTS completed in {tts_duration:.3f}s")
        
        # ========== Save to Chat History ==========
        session_store.add_chat_message(session_id, "user", native_question)
        session_store.add_chat_message(session_id, "assistant", native_answer)
        
        # ========== Audit Log ==========
        db_session = db.get_session()
        try:
            audit = AuditLog(
                customer_id=session_id,
                endpoint="/api/voice/converse",
                recommendation={
                    "user_message": native_question,
                    "english_message": english_question,
                    "language": language_code,
                    "tool_calls": tool_calls_made
                },
                reasoning={"assistant_response": native_answer, "english_response": english_answer},
                model_version="groq-llama-3.1+sarvam-ai"
            )
            db_session.add(audit)
            db_session.commit()
        except Exception as e:
            print(f"Audit log failed in voice conversation: {e}")
            db_session.rollback()
        finally:
            db_session.close()
        
        # ========== Return Response ==========
        total_duration = time.time() - start_time
        print(f"[{get_timestamp()}] [VOICE] Total voice conversation completed in {total_duration:.3f}s")
        
        return JSONResponse({
            "audio": audio_base64,
            "native_question": native_question,
            "native_answer": native_answer,
            "english_question": english_question,
            "english_answer": english_answer,
            "tool_calls_made": tool_calls_made,
            "processing_time": {
                "stt": round(stt_duration, 3),
                "llm": round(groq_duration, 3),
                "translation": round(translation_duration, 3),
                "tts": round(tts_duration, 3),
                "total": round(total_duration, 3)
            }
        })
        
    except Exception as e:
        print(f"[{get_timestamp()}] [VOICE] Error in voice conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice conversation error: {str(e)}"
        )


@router.get("/voice/status", tags=["Voice AI"])
async def voice_service_status():
    """
    Check if voice AI services are available and configured
    """
    return {
        "status": "operational" if sarvam_client else "not_configured",
        "sarvam_configured": sarvam_client is not None,
        "sdk_available": SarvamAI is not None,
        "message": "Voice AI services ready" if sarvam_client else "SARVAM_API_KEY not configured"
    }


@router.post("/voice/greet", tags=["Voice AI"])
async def voice_greet(
    session_id: str = Form(..., description="Session ID (profile ID)"),
    language_code: str = Form(..., description="Language code (e.g., hi-IN, ta-IN, en-IN)"),
    speaker_gender: Optional[str] = Form("Female", description="Speaker gender for TTS voice")
):
    """
    Generate a spoken greeting for the user in their selected language.
    Called when the chat panel opens to welcome the user by name.

    Pipeline:
    1. Fetch user name from session store
    2. Build greeting in English
    3. Translate to native language (Sarvam Mayura v1) — skip if English
    4. Generate TTS audio (Sarvam Bulbul v3)
    5. Return { greeting_text, audio }
    """
    # Verify session exists
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )

    # Get first name for a personal greeting
    full_name = profile.get("name", "there")
    first_name = full_name.split()[0] if full_name else "there"

    # Build a warm, conversational English greeting (voice-mode style: short, spoken)
    english_greeting = (
        f"Hello {first_name}! I'm your IDBI Wealth AI assistant. "
        f"How can I help you with your finances today?"
    )

    try:
        # If no Sarvam client, return text-only greeting (no audio)
        if not sarvam_client:
            print(f"[VOICE GREET] Sarvam client not configured — returning text-only")
            return JSONResponse({
                "greeting_text": english_greeting,
                "audio": None,
                "language_code": language_code
            })

        print(f"[VOICE GREET] Request: session={session_id}, lang={language_code}, gender={speaker_gender}")

        # ---- Translate if not English ----
        if language_code == "en-IN":
            native_greeting = english_greeting
            print(f"[VOICE GREET] Skipping translation (English)")
        else:
            print(f"[VOICE GREET] Translating to {language_code}...")
            try:
                translation_response = sarvam_client.text.translate(
                    input=english_greeting,
                    source_language_code="en-IN",
                    target_language_code=language_code,
                    model="mayura:v1",
                    mode="modern-colloquial",
                    speaker_gender=speaker_gender
                )
                native_greeting = translation_response.translated_text
                print(f"[VOICE GREET] Translated: \"{native_greeting}\"")
            except Exception as te:
                print(f"[VOICE GREET] Translation FAILED: {te}")
                native_greeting = english_greeting  # fallback to English

        # ---- Generate TTS audio ----
        speaker = "neha" if speaker_gender == "Female" else "rahul"
        print(f"[VOICE GREET] Calling TTS: speaker={speaker}, text=\"{native_greeting[:60]}...\"")

        try:
            tts_response = sarvam_client.text_to_speech.convert(
                text=native_greeting,
                target_language_code=language_code,
                model="bulbul:v3",
                speaker=speaker,
                pace=1.0,
                speech_sample_rate=24000
            )

            # Sarvam SDK returns `.audios` (list of base64 strings), not `.audio`
            audio_val = tts_response.audios
            print(f"[VOICE GREET] TTS audios: type={type(audio_val)}, "
                  f"count={len(audio_val) if isinstance(audio_val, list) else 'N/A'}")

            # Sarvam SDK may return a list of base64 chunks — take the first one
            if isinstance(audio_val, list):
                audio_out = audio_val[0] if audio_val else None
                print(f"[VOICE GREET] Audio is list of {len(audio_val)} chunk(s), using first")
            else:
                audio_out = audio_val

            if audio_out:
                print(f"[VOICE GREET] Returning audio of length {len(str(audio_out))} chars")
            else:
                print(f"[VOICE GREET] WARNING: audio_out is empty/None")

            return JSONResponse({
                "greeting_text": native_greeting,
                "audio": audio_out,
                "language_code": language_code
            })

        except Exception as tts_err:
            import traceback
            print(f"[VOICE GREET] TTS FAILED: {tts_err}")
            traceback.print_exc()
            # Return text without audio if TTS fails
            return JSONResponse({
                "greeting_text": native_greeting,
                "audio": None,
                "language_code": language_code
            })

    except Exception as e:
        import traceback
        print(f"[VOICE GREET] Unexpected error: {e}")
        traceback.print_exc()
        # Graceful fallback: return text greeting without audio
        return JSONResponse({
            "greeting_text": english_greeting,
            "audio": None,
            "language_code": language_code
        })

