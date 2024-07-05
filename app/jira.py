import requests
import logging
import os
from app.models import Message
from app.config import channel_jira_mapping

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


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
            print(f"No user found with email: {email}")
            return None
    else:
        print(f"Failed to search for user: {response.status_code}")
        print(response.text)
        return None



def create_jira_ticket(message: Message):
    try:
        # Get Jira project key, epic, and board ID from mapping
        mapping = channel_jira_mapping.get(message.channel)
        project_key = mapping.get("project_key", "DEFAULT_PROJECT_KEY")
        parent_key = mapping.get("epic", "DEFAULT_EPIC_KEY")
        board_id = mapping.get("board_id", "DEFAULT_BOARD_ID")


        url = f"{JIRA_URL}/rest/api/3/issue"
        auth = (JIRA_USERNAME, JIRA_API_TOKEN)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": f"Slack Request {message.user}",
                "description": {
                    "type": "doc",
                    "version": 1,
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
                "issuetype": {
                    "name": "Task"
                },
                "parent": {
                    "key": parent_key
                },
                "assignee": {
                    "accountId": get_jira_account_id(message.reactions.user)
                },
                "reporter": {
                    "accountId": get_jira_account_id(message.user)
                },
                "customfield_10020": get_current_sprint(board_id)
            }
        }
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        logging.info(f"Jira ticket created successfully: {response.json()}")
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e}")
        logging.error(f"Response content: {e.response.content}")
    except Exception as e:
        logging.error(f"Error creating Jira ticket: {e}")