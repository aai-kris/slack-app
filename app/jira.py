import requests
import logging
import os
from dotenv import load_dotenv
from app.models import Message
from app.config import channel_jira_mapping

# Load environment variables from .env file
load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
SLACK_WORKSPACE_URL = os.getenv("SLACK_WORKSPACE_URL")

def get_current_sprint(board_id: str) -> int:
    try:
        url = f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint?state=active"
        auth = (JIRA_USERNAME, JIRA_API_TOKEN)
        headers = {
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        sprints = response.json().get("values", [])
        if sprints:
            return sprints[0]["id"]
        return None
    except Exception as e:
        logging.error(f"Error fetching current sprint: {e}")
        return None

def get_jira_account_id(email) -> str:
    search_url = f"{JIRA_URL}/rest/api/3/user/search"
    auth = (JIRA_USERNAME, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json"
    }
    params = {
        "query": email
    }
    response = requests.get(
        search_url,
        headers=headers,
        auth=auth,
        params=params
    )
    if response.status_code == 200:
        users = response.json()
        if users:
            return users[0]['accountId']
        else:
            logging.error(f"No user found with email: {email}")
            return None
    else:
        logging.error(f"Failed to search for user: {response.status_code}")
        logging.error(response.text)
        return None

def create_jira_ticket(message: Message) -> [str]:
    try:
        mapping = channel_jira_mapping.get(message.channel)

        project_key = mapping.get("project_key", "TPM")
        parent_key = mapping.get("epic", "TPM-36")
        board_id = mapping.get("board_id", "45")

        url = f"{JIRA_URL}/rest/api/3/issue"
        auth = (JIRA_USERNAME, JIRA_API_TOKEN)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Construct Slack message URL
        slack_message_url = f"{SLACK_WORKSPACE_URL}/archives/{message.channel}/p{message.ts.replace('.', '')}"

        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": f"Slack Request from {message.user.name}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "blockquote",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": message.text
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "\nSlack message link: "
                                },
                                {
                                    "type": "text",
                                    "text": "here",
                                    "marks": [
                                        {
                                            "type": "link",
                                            "attrs": {
                                                "href": slack_message_url
                                            }
                                        }
                                    ]
                                }
                            ]
                        },

                    ]
                },
                "issuetype": {
                    "name": "Task"
                },
                "parent": {
                    "key": parent_key
                },
                "assignee": {
                    "accountId": get_jira_account_id(message.reactions.user.email)
                },
                "reporter": {
                    "accountId": get_jira_account_id(message.user.email)
                },
                "customfield_10020": get_current_sprint(board_id)
            }
        }
        logging.info(f"Creating Jira ticket with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        logging.info(f"Jira ticket created successfully: {response.json()}")

        issue_key = response.json().get("key")
        logging.info(f"Jira ticket key: {issue_key}")

        jira_issue_url = f"{JIRA_URL}/browse/{issue_key}"
        logging.info(f"Jira ticket url: {jira_issue_url}")

        return [issue_key, jira_issue_url]

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err.response.content}")
        return None
    except Exception as e:
        logging.error(f"Error creating Jira ticket: {e}")
        return None
