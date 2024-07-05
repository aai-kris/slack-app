from fastapi import FastAPI, Request, HTTPException
import logging
from app.slack import message_handler, signature_verifier, parse_slack_payload
from app.jira import create_jira_ticket

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/slack/events")
async def slack_events(request: Request):
    if not signature_verifier.is_valid_request(await request.body(), request.headers):
        raise HTTPException(status_code=400, detail="Invalid request signature")

    payload = await request.json()

    # URL Verification Challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Parse the initial Slack event
    event = parse_slack_payload(payload)

    # Check for engineer reaction being added
    if event.reaction == "engineer" and event.type == "reaction_added":

        # Get the content of the message if the emoji is being used for the first time
        message = message_handler(event.item.channel, event.item.ts, "engineer")

        # create a Jira ticket if the message object returns
        if message:
            create_jira_ticket(message)
            return {"status": "ok"}

    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
