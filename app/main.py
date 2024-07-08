from fastapi import FastAPI, Request, HTTPException
import logging
from app.slack import slack_handler, signature_verifier

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/slack/events")
async def slack_events(request: Request):

    if not signature_verifier.is_valid_request(await request.body(), request.headers):
        raise HTTPException(status_code=400, detail="Invalid request signature")

    payload = await request.json()
    logging.info(f"Payload received: {payload}")

    response = slack_handler(payload)
    logging.info(f"Handler response: {response}")

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
