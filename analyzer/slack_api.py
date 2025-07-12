import requests
import sys

def fetch_slack_messages(channel_id: str, bot_token: str, oldest: int, latest: int) -> list:
    """
    Fetch messages from Slack API conversation history endpoint.

    Args:
        channel_id (str): Slack channel ID.
        bot_token (str): Slack Bot OAuth token.
        oldest (int): Unix timestamp of the start time.
        latest (int): Unix timestamp of the end time.

    Returns:
        list: List of Slack messages dicts.

    Exits program if error occurs.
    """
    url = "https://slack.com/api/conversations.history"
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    params = {
        "channel": channel_id,
        "oldest": oldest,
        "latest": latest,
        "limit": 1000,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            print(f"Slack API Error: {data.get('error', 'Unknown error')}")
            sys.exit(1)

        return data.get("messages", [])

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        sys.exit(1)