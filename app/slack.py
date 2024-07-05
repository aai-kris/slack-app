import ssl
import certifi
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient
import logging
import os
from dotenv import load_dotenv
from app.models import ReactionEvent, ItemEvent, Message, Reactions


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


# Check the reaction is an :engineer: reaction and the first use of it on the message
def check_reaction(channel: str, timestamp: str, reaction: str) -> bool:
    try:
        response = slack_client.reactions_get(
            channel=channel,
            timestamp=timestamp
        )
        reactions = response.get("message", {}).get("reactions", [])

        for react in reactions:
            if react["name"] == reaction and react["count"] == 1:
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking reactions: {e}")
        return False

def get_user_email(user_id: str) -> str:
    try:
        response = slack_client.users_info(user=user_id)
        email = response.get("user", {}).get("profile", {}).get("email", "")
        return email
    except Exception as e:
        logging.error(f"Error fetching user email: {e}")
        return ""


def message_handler(channel: str, timestamp: str, reaction: str) -> Message:
    try:
        # Check the reaction is an :engineer: reaction and the first use of it on the message
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
                    user=get_user_email(users[0]),
                    count=reactions[0].get("count")
                )
                message = Message(
                    user=get_user_email(messages[0].get("user", None)),
                    text=messages[0].get("text", None),
                    channel=channel,
                    ts=timestamp,
                    reactions=reactions
                )

                return message
            return None
    except Exception as e:
        logging.error(f"Error fetching message content: {e}")
        return None
