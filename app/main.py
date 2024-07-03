import ssl
import certifi
from fastapi import FastAPI, Request, HTTPException
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient
import logging
import os
from dotenv import load_dotenv
from app.models import ReactionEvent, ItemEvent, Message, Reactions

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

ssl_context = ssl.create_default_context(cafile=certifi.where())
slack_client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)

def parse_slack_payload(payload: dict) -> ReactionEvent:
    event_data = payload["event"]
    item_data = event_data["item"]
    item_event = ItemEvent(
        type=item_data["type"],
        channel=item_data.get("channel"),
        ts=item_data.get("ts")
    )
    event = ReactionEvent(
        type=event_data["type"],
        user=event_data["user"],
        reaction=event_data["reaction"],
        item_user=event_data["item_user"],
        item=item_event
    )
    return event




# def get_message_content(channel: str, timestamp: str) -> str:
#     try:
#         response = slack_client.conversations_replies(
#             channel=channel,
#             ts=timestamp,
#             inclusive=True,
#             limit=1
#         )
#         messages = response.get("messages", [])
#         print(messages)
#         if messages:
#             print(f'User ID who sent message: {messages[0].get("user", "")}')
#             print(f'Message: {messages[0].get("text", "")}')
#             print(f'Reaction: {messages[0].get("reactions", [])}')
#             return messages[0].get("text", "")
#         return ""
#     except Exception as e:
#         logging.error(f"Error fetching message content: {e}")
#         return ""

def check_reaction(channel: str, timestamp: str, reaction: str) -> bool:
    try:
        response = slack_client.reactions_get(
            channel=channel,
            timestamp=timestamp
        )
        reactions = response.get("message", {}).get("reactions", [])
        # print(reactions)
        for react in reactions:
            if react["name"] == reaction and react["count"] == 1:
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking reactions: {e}")
        return False


def message_handler(channel: str, timestamp: str, reaction: str) -> Message:
    try:
        # If this returns true, then we want to go ahead and return the message
        if check_reaction(channel, timestamp, reaction):

            response = slack_client.conversations_replies(
                channel=channel,
                ts=timestamp,
                inclusive=True,
                limit=1
            )
            messages = response.get("messages", [])

            if messages:
                reactions = messages[0].get("reactions", [])
                users = reactions[0].get("users", [])

                reactions = Reactions(
                    name=reactions[0].get("name"),
                    user=users[0],
                    count=reactions[0].get("count")
                )
                message = Message(
                    user=messages[0].get("user", None),
                    text=messages[0].get("text", None),
                    reactions=reactions
                )

                return message

            return None
    except Exception as e:
        logging.error(f"Error fetching message content: {e}")
        return None




@app.post("/slack/events")
async def slack_events(request: Request):
    if not signature_verifier.is_valid_request(await request.body(), request.headers):
        raise HTTPException(status_code=400, detail="Invalid request signature")

    payload = await request.json()

    # URL Verification Challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Parse the event
    event = parse_slack_payload(payload)

    # Engineer Reaction Detected and does not already exist
    if event.reaction == "engineer":

        # Event is an engineer reaction being added
        if event.type == 'reaction_added':

            # Check if the reaction already exists
            # if not check_reaction(event.item.channel, event.item.ts, "engineer"):

            # Get the content of the message
            message = message_handler(event.item.channel, event.item.ts, "engineer")
            print(message)
            print("Run a function to add a ticket to Jira")


        if event.type == 'reaction_removed':
            logging.info(f"User {event.user} removed reaction {event.reaction} to item {event.item.channel} by user {event.item_user}")

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
