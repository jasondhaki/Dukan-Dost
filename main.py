from fastapi import FastAPI

# Create the main app object
app = FastAPI()

# Define a "route" for the main URL ("/")
@app.get("/")
def read_root():
    # Return a simple JSON response
    return {"message": "DukanDost API is running!"}