from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import database  # Import our new database file

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "DukanDost API is running!"}

@app.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form(...)):
    # Show received message
    print(f"Message received from: {From}")
    print(f"Message body: {Body}")
    
    # Save message to database
    try:
        database.save_message(From, Body)
    except Exception as e:
        print(f"Database save error: {e}")

    # Reply back
    response = MessagingResponse()
    reply_message = f"You sent: '{Body}'. We are processing it!"
    response.message(reply_message)
    
    return Response(content=str(response), media_type="application/xml")
