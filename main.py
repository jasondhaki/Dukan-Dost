import os                  # NEW: To read environment variables
import requests            # NEW: To make web requests to Hugging Face
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import database
from typing import Optional  # NEW: To handle optional form fields
from dotenv import load_dotenv # NEW: To load our .env file

# NEW: Load the .env file (it will find the HF_API_KEY)
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY") # NEW: Get the key from the environment
HF_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3" # NEW: Whisper AI model

app = FastAPI()

# NEW: This is the function that does the "magic"
def transcribe_audio(audio_url: str) -> str:
    if not HF_API_KEY:
        return "ERROR: Hugging Face API key not set."

    # 1. Set up the authorization headers
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # 2. Download the audio file from Twilio's URL
    try:
        audio_response = requests.get(audio_url)
        audio_response.raise_for_status() # Check for download errors
        audio_data = audio_response.content
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return "ERROR: Could not download audio file."

    # 3. Send the downloaded audio data to Hugging Face
    try:
        response = requests.post(HF_API_URL, headers=headers, data=audio_data)
        response.raise_for_status() # Check for API errors
        
        result = response.json()
        
        # 4. Check the result and return the text
        if "error" in result:
            print(f"Hugging Face Error: {result['error']}")
            return f"ERROR: {result['error']}"
        
        transcribed_text = result.get("text", "ERROR: No text found in response.")
        return transcribed_text
        
    except Exception as e:
        print(f"Error calling Hugging Face API: {e}")
        return "ERROR: AI service failed."


@app.get("/")
def read_root():
    return {"message": "DukanDost API is running!"}

# UPDATED: The webhook now accepts media files
@app.post("/webhook")
async def webhook(
    From: str = Form(...), 
    Body: str = Form(...),
    NumMedia: int = Form(0),          # NEW: Check if media was sent (0 = no)
    MediaUrl0: Optional[str] = Form(None) # NEW: The URL of the media file
):
    
    print(f"--- New Request from {From} ---")
    response = MessagingResponse()
    
    # NEW: Check if it's a media message or a text message
    if NumMedia > 0 and MediaUrl0 is not None:
        # It's a voice note!
        print("Media message received. Transcribing...")
        
        # Call our new function
        transcribed_text = transcribe_audio(MediaUrl0)
        
        print(f"Transcribed Text: {transcribed_text}")
        reply_message = f"I heard: '{transcribed_text}'"
        
    else:
        # It's a plain text message (Day 2 logic)
        print(f"Text message received: {Body}")
        database.save_message(From, Body) # Save text to DB
        reply_message = f"You sent: '{Body}'. Send me a voice note!"

    # Send the reply
    response.message(reply_message)
    return Response(content=str(response), media_type="application/xml")