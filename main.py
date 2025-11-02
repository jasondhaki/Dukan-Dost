import os
import speech_recognition as sr  # NEW: Import SpeechRecognition
from pydub import AudioSegment     # NEW: Import pydub
import io                          # NEW: To handle file data in memory

from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import database
from typing import Optional
from dotenv import load_dotenv
import requests

# Load .env secrets
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI()

# NEW: This function uses Google's free API
def transcribe_audio_google(audio_url: str) -> str:
    # 1. Download the protected Twilio audio file
    try:
        audio_response = requests.get(audio_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        audio_response.raise_for_status()
        audio_data = audio_response.content
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return "ERROR: Could not download audio file."

    # 2. Convert the audio from .ogg to .wav
    try:
        # Tell pydub where to find ffmpeg (right in our folder)
        AudioSegment.converter = "./ffmpeg.exe" 
        AudioSegment.ffprobe = "./ffprobe.exe"

        # Load the audio data (which is in .ogg format) from memory
        ogg_audio = AudioSegment.from_file(io.BytesIO(audio_data), format="ogg")

        # Prepare to export it as .wav to a new in-memory file
        wav_io = io.BytesIO()
        ogg_audio.export(wav_io, format="wav")
        wav_io.seek(0)  # Rewind the in-memory file to the beginning
    except Exception as e:
        print(f"Error converting audio: {e}")
        return "ERROR: Could not convert audio file."

    # 3. Transcribe the .wav file using Google's API
    r = sr.Recognizer()
    try:
        # Load the .wav data into the recognizer
        with sr.AudioFile(wav_io) as source:
            audio = r.record(source)

        # Call the Google API to transcribe (specifically for Bengali)
        # This is FREE and requires NO key
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


@app.get("/")
def read_root():
    return {"message": "DukanDost API is running!"}

@app.get("/test")
def read_test():
    print("!!! BROWSER TEST WORKED !!!")
    return {"message": "Success! The ngrok tunnel is working!"}

# UPDATED: The webhook now accepts media files
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

        # Call our NEW function
        transcribed_text = transcribe_audio_google(MediaUrl0)

        print(f"Transcribed Text: {transcribed_text}")
        reply_message = f"I heard: '{transcribed_text}'"

    else:
        # It's a plain text message
        print(f"Text message received: {Body}")
        database.save_message(From, Body)
        reply_message = f"You sent: '{Body}'. Send me a voice note!"

    # Send the reply
    response.message(reply_message)
    return Response(content=str(response), media_type="application/xml")