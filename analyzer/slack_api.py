import requests

class SlackAPIError(Exception):
    pass

def fetch_slack_messages(channel_id: str, bot_token: str, oldest: int, latest: int, limit: int = 1000):
    """
    Fetch messages from a Slack channel within a time window.
    
    Args:
        channel_id (str): Slack channel ID.
        bot_token (str): Slack bot token.
        oldest (int): Unix timestamp for oldest message.
        latest (int): Unix timestamp for latest message.
        limit (int): Max number of messages to fetch (default 1000).
    
    Returns:
        List[dict]: List of Slack messages.
    
    Raises:
        SlackAPIError: If Slack API returns error.
        requests.exceptions.RequestException: For HTTP/network issues.
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
        "limit": limit
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Log or re-raise with context
        raise e

    data = response.json()
    if not data.get("ok", False):
        raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
    
    return data.get("messages", [])