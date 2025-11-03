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
import numpy as np         # <--- ADD THIS
import cv2                 # <--- ADD THIS
import easyocr             # <--- ADD THIS

# Load .env secrets
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI()
# NEW: Initialize the OCR Reader (This runs once on startup)
# It will download the models the first time it runs
print("Loading EasyOCR models (bn=Bengali, en=English)...")
ocr_reader = easyocr.Reader(['bn', 'en'])
print("EasyOCR models loaded.")

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


# --- NEW FUNCTION FOR DAY 5 (Fuzzier Parser) ---
def parse_message(text: str) -> dict:
    """
    A simple parser to find item, quantity, and price.
    This version is "fuzzier" to handle OCR errors.
    """
    known_items = ['চাল', 'ডাল', 'hello']
    
    words = text.split() 
    
    parsed_data = {
        "item_name": None,
        "quantity": None,
        "price": None
    }
    
    try:
        # Loop through words to find both item name and quantity
        for i, word in enumerate(words):
            # 1. Find the Item Name (Accept 'I' as a typo for 'ল')
            if 'চাল' in word or 'চান' in word or 'চIন' in word:
                # Standardize the item name to 'চাল'
                parsed_data["item_name"] = 'চাল'
            elif 'ডাল' in word:
                parsed_data["item_name"] = 'ডাল'
            elif 'hello' in word:
                 parsed_data["item_name"] = 'hello'

            # 2. Find Quantity (Look for numbers anywhere)
            if word.isdigit():
                parsed_data["quantity"] = int(word)
                
            # 3. Find Price (Look for words near 'টাকা')
            if 'টাকা' in word or 'taka' in word:
                if i > 0 and words[i-1].isdigit(): 
                    parsed_data["price"] = int(words[i-1])

        # Post-processing: If we found a quantity, ensure we have an item.
        # This simplifies the logic by assuming the item is found somewhere near the number.
        if parsed_data["quantity"] and not parsed_data["item_name"]:
            # This is a hack for a messy parse: assume the next word is the item
            next_index = words.index(str(parsed_data["quantity"])) + 1
            if next_index < len(words):
                if 'চাল' in words[next_index] or 'চান' in words[next_index]:
                    parsed_data["item_name"] = 'চাল'

    except Exception as e:
        print(f"Parser Error: {e}")
        
    return parsed_data
# --- END OF NEW FUNCTION ---

# --- NEW FUNCTION FOR DAY 5 ---
def transcribe_image_ocr(image_url: str) -> str:
    """Downloads an image from Twilio and uses EasyOCR to read handwritten text."""
    try:
        # 1. Download the protected Twilio image
        image_response = requests.get(image_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        image_response.raise_for_status()
        
        # 2. Convert the downloaded image data (bytes) into a format CV2 can read
        image_array = np.frombuffer(image_response.content, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    except Exception as e:
        print(f"Error downloading or processing image: {e}")
        return "ERROR: Could not read image file."

    try:
        # 3. Use EasyOCR to read the text from the image
        # 'detail = 0' makes it faster and just returns a list of strings
        result = ocr_reader.readtext(img, detail=0)
        
        # 4. Stitch all the found text blocks into one single string
        transcribed_text = " ".join(result)
        return transcribed_text
        
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return "ERROR: AI service failed."
# --- END OF NEW FUNCTION ---

@app.get("/")
def read_root():
    return {"message": "DukanDost API is running!"}

@app.get("/test")
def read_test():
    print("!!! BROWSER TEST WORKED !!!")
    return {"message": "Success! The ngrok tunnel is working!"}


# --- UPDATED WEBHOOK FOR DAY 5 ---
@app.post("/webhook")
async def webhook(
    From: str = Form(...), 
    Body: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):

    print(f"--- New Request from {From} ---")
    response = MessagingResponse()
    
    # This variable will be set by one of the paths
    reply_message = "" 

    if NumMedia > 0 and MediaUrl0 is not None:
        # --- THIS ENTIRE BLOCK IS NOW INDENTED ---
        transcribed_text = ""
        
        # Check if the media content type contains "image"
        if MediaContentType0 and "image" in MediaContentType0:
            # IT'S AN IMAGE!
            print("Image message received. Transcribing with OCR...")
            transcribed_text = transcribe_image_ocr(MediaUrl0)

        # Check if the media content type contains "audio" or "ogg"
        elif MediaContentType0 and ("audio" in MediaContentType0 or "ogg" in MediaContentType0):
            # IT'S A VOICE NOTE!
            print("Audio message received. Transcribing with Google...")
            transcribed_text = transcribe_audio_google(MediaUrl0)

        else:
            # It's some other media (video, gif?) we don't support
            print(f"Unsupported media type: {MediaContentType0}")
            reply_message = "I can only understand voice notes and photos of ledgers."
            response.message(reply_message)
            return Response(content=str(response), media_type="application/xml")

        # --- From here, the Day 4 logic is the same (and also indented) ---
        
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
        
        elif not transcribed_text.startswith("ERROR:"):
            # Just random speech that wasn't an error
            reply_message = f"I heard: '{transcribed_text}' \n(I only understand sales, like '৫ কেজি চাল ২৫০ টাকা')"
        
        else:
            # This catches errors from transcription
            reply_message = transcribed_text # e.g., "ERROR: Could not convert audio file."

    else:
        # It's a plain text message (Day 2 logic)
        print(f"Text message received: {Body}")
        database.save_message(From, Body)
        reply_message = f"You sent: '{Body}'. Send me a voice note or photo!"

    # Send the reply (This runs for all paths)
    response.message(reply_message)
    return Response(content=str(response), media_type="application/xml")