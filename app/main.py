from fastapi import FastAPI, Request, HTTPException
import logging
from app.slack import slack_handler, signature_verifier

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/slack/events")
async def slack_events(request: Request):
    logging.info("Received a Slack event")
    try:
        if not signature_verifier.is_valid_request(await request.body(), request.headers):
            logging.error("Invalid request signature")
            raise HTTPException(status_code=400, detail="Invalid request signature")

        payload = await request.json()
        logging.info(f"Payload received: {payload}")

        response = slack_handler(payload)
        logging.info(f"Handler response: {response}")

        return response
    except HTTPException as http_exc:
        logging.error(f"HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logging.error(f"Unhandled exception occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
