import ssl
import certifi
from slack_sdk.signature import SignatureVerifier
from slack_sdk import WebClient
import requests
import logging
import os
from dotenv import load_dotenv
from app.models import ReactionEvent, ItemEvent, Message, Reactions, Person
from app.jira import create_jira_ticket
import hashlib
import sqlite3


# Load environment variables from .env file
load_dotenv()

SLACK_EMOJI = "engineer"
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

ssl_context = ssl.create_default_context(cafile=certifi.where())
slack_client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)

# Initialize SQLite connection
conn = sqlite3.connect("processed_events.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS processed_events (id TEXT PRIMARY KEY)''')
conn.commit()

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

def is_engineer_reaction(channel: str, timestamp: str, reaction: str) -> bool:
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


def get_user_info(user_id: str) -> Person:
    try:
        response = slack_client.users_info(user=user_id)
        user_info = response.get("user", {}).get("profile", {})
        return Person(name=user_info.get("real_name", ""), email=user_info.get("email", ""))
    except Exception as e:
        logging.error(f"Error fetching user info: {e}")
        return Person(name="", email="")

def message_handler(channel: str, timestamp: str, reaction: str) -> Message:
    try:
        # Check the reaction is an :engineer: reaction and the first use of it on the message
        if is_engineer_reaction(channel, timestamp, reaction):

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
                    user=get_user_info(users[0]),
                    count=reactions[0].get("count")
                )
                message = Message(
                    user=get_user_info(messages[0].get("user", None)),
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

def post_message_to_slack(message, jiraID, jiraUrl):
    slack_url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": message.channel,
        "text": f"Your request has been picked up by {message.reactions.user.name} \n\n <{jiraUrl}|{jiraID}>",
        "thread_ts": message.ts
    }
    response = requests.post(slack_url, headers=headers, json=payload)
    if response.status_code == 200:
        logging.info("Message posted to Slack successfully.")
    else:
        logging.error(f"Failed to post message to Slack: {response.status_code}, {response.text}")

def generate_idempotency_key(event: ReactionEvent) -> str:
    key_string = f"{event.type}-{event.user}-{event.item.channel}-{event.item.ts}-{event.reaction}"
    return hashlib.sha256(key_string.encode()).hexdigest()

def check_event_processed(idempotency_key: str) -> bool:
    c.execute("SELECT id FROM processed_events WHERE id = ?", (idempotency_key,))
    return c.fetchone() is not None

def mark_event_processed(idempotency_key: str):
    c.execute("INSERT INTO processed_events (id) VALUES (?)", (idempotency_key,))
    conn.commit()

def slack_handler(payload):
    # URL Verification Challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Parse the initial Slack event
    event = parse_slack_payload(payload)
    logging.info(f"Slack event parsed: {event}")

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(event)
    logging.info(f"Generated idempotency key: {idempotency_key}")

    # Check if event has been processed
    if check_event_processed(idempotency_key):
        logging.info(f"Event with idempotency key {idempotency_key} already processed.")
        return {"status": "ignored"}


    # Check for engineer reaction being added
    if event.reaction == SLACK_EMOJI and event.type == "reaction_added":

        # Get the content of the message if the emoji is being used for the first time
        message = message_handler(event.item.channel, event.item.ts, SLACK_EMOJI)
        logging.info(message)

        # create a Jira ticket if the message object returns
        if message:
            logging.info("Creating Jira ticket.")
            jiraTicket = create_jira_ticket(message)
            logging.info(f"Jira ticket created: {jiraTicket}")
            post_message_to_slack(message, jiraTicket[0], jiraTicket[1])

            # Mark the event as processed
            mark_event_processed(idempotency_key)
            return {"status": "ok"}

    return {"status": "ignored"}
