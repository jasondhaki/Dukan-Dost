import os
import speech_recognition as sr
from pydub import AudioSegment
import io

from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import database  # This will now import your new inventory functions
from typing import Optional
from dotenv import load_dotenv
import requests

# Load .env secrets
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI()

# --- DAY 3'S VOICE FUNCTION (Unchanged) ---
def transcribe_audio_google(audio_url: str) -> str:
    try:
        audio_response = requests.get(audio_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        audio_response.raise_for_status()
        audio_data = audio_response.content
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return "ERROR: Could not download audio file."

    try:
        AudioSegment.converter = "./ffmpeg.exe"
        AudioSegment.ffprobe = "./ffprobe.exe"
        ogg_audio = AudioSegment.from_file(io.BytesIO(audio_data), format="ogg")
        wav_io = io.BytesIO()
        ogg_audio.export(wav_io, format="wav")
        wav_io.seek(0)
    except Exception as e:
        print(f"Error converting audio: {e}")
        return "ERROR: Could not convert audio file."

    r = sr.Recognizer()
    try:
        with sr.AudioFile(wav_io) as source:
            audio = r.record(source)
        transcribed_text = r.recognize_google(audio, language="bn-BD")
        return transcribed_text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return "ERROR: I could not understand what you said."
    except sr.RequestError as e:
        print(f"Google Speech Recognition error: {e}")
        return "ERROR: Google's speech service is down."
    except Exception as e:
        print(f"A new error occurred: {e}")
        return "ERROR: AI service failed."


# --- NEW FUNCTION FOR DAY 4 ---
def parse_message(text: str) -> dict:
    """
    A simple parser to find item, quantity, and price.
    This is the "AI" for the hackathon.
    Example: "আজকের বিক্রি ৫ কেজি চাল ২৫০ টাকা"
    """
    # Keywords we are looking for (must match database.py)
    known_items = ['চাল', 'ডাল', 'hello']

    words = text.split() # Split the text into a list of words

    parsed_data = {
        "item_name": None,
        "quantity": None,
        "price": None
    }

    try:
        # 1. Find the item
        for word in words:
            if word in known_items:
                parsed_data["item_name"] = word
                break # Found it!

        # 2. Find the quantity (look for 'কেজি' or 'kg')
        for i, word in enumerate(words):
            if word == 'কেজি' or word == 'kg':
                if i > 0 and words[i-1].isdigit(): # Make sure there's a number before it
                    parsed_data["quantity"] = int(words[i-1])
                    break

        # 3. Find the price (look for 'টাকা' or 'taka')
        for i, word in enumerate(words):
            if word == 'টাকা' or word == 'taka':
                if i > 0 and words[i-1].isdigit(): # Make sure there's a number before it
                    parsed_data["price"] = int(words[i-1])
                    break

        # This is a fallback for simple messages like "hello 5"
        if parsed_data["item_name"] == "hello" and parsed_data["quantity"] is None:
            for word in words:
                if word.isdigit():
                    parsed_data["quantity"] = int(word)
                    break

    except Exception as e:
        print(f"Parser Error: {e}")
        # Don't stop, just return what we found

    return parsed_data
# --- END OF NEW FUNCTION ---


@app.get("/")
def read_root():
    return {"message": "DukanDost API is running!"}

@app.get("/test")
def read_test():
    print("!!! BROWSER TEST WORKED !!!")
    return {"message": "Success! The ngrok tunnel is working!"}


# --- UPDATED WEBHOOK FOR DAY 4 ---
@app.post("/webhook")
async def webhook(
    From: str = Form(...), 
    Body: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: Optional[str] = Form(None)
):

    print(f"--- New Request from {From} ---")
    response = MessagingResponse()

    if NumMedia > 0 and MediaUrl0 is not None:
        # It's a voice note!
        print("Media message received. Transcribing...")

        # Step 1: Transcribe the audio
        transcribed_text = transcribe_audio_google(MediaUrl0)
        print(f"Transcribed Text: {transcribed_text}")

        # Step 2: Parse the text to get data
        parsed_data = parse_message(transcribed_text)
        print(f"Parsed Data: {parsed_data}")

        item = parsed_data.get("item_name")
        quantity = parsed_data.get("quantity")

        # Step 3: Use the data!
        if item and quantity:
            # We have an item and a quantity! Let's update stock.
            print(f"Updating stock for {item}...")
            stock_update = database.update_stock(item, quantity)

            if "error" in stock_update:
                reply_message = f"Error: {stock_update['error']}"
            else:
                # This is the "Smart Alert"!
                new_stock = stock_update['new_stock']
                reply_message = f"✅ Sale logged: {quantity} {item}. \nNew stock is: {new_stock}."

                if stock_update['alert_needed']:
                    # Add the alert!
                    reply_message += f"\n\n🚨 LOW STOCK ALERT! 🚨\nYour stock for {item} is at {new_stock}. Time to reorder!"

        elif item and not quantity:
            # Found item, but no quantity
            reply_message = f"I heard you mention '{item}', but I didn't understand the quantity. Try '৫ কেজি চাল' (5 kg rice)."
        else:
            # Just random speech
            reply_message = f"I heard: '{transcribed_text}' \n(I only understand sales, like '৫ কেজি চাল ২৫০ টাকা')"

    else:
        # It's a plain text message
        print(f"Text message received: {Body}")
        database.save_message(From, Body)
        reply_message = f"You sent: '{Body}'. Send me a voice note!"

    # Send the reply
    response.message(reply_message)
    return Response(content=str(response), media_type="application/xml")