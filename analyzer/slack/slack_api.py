import requests
from pathlib import Path
from typing import Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError as SdkSlackApiError

class SlackAPIError(Exception):
    pass

def fetch_slack_messages(channel_id: str, bot_token: str, oldest: int, latest: int, limit: int = 1000):
    """
    Fetch messages from a Slack channel within a time window using Slack SDK.

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
    """
    # Create Slack client
    client = WebClient(token=bot_token)

    try:
        # Use conversations_history from SDK
        response = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest),
            latest=str(latest),
            limit=limit
        )

        if not response.get("ok", False):
            raise SlackAPIError(f"Slack API error: {response.get('error', 'Unknown error')}")

        return response.get("messages", [])

    except SdkSlackApiError as e:
        raise SlackAPIError(f"Slack API error: {e.response['error']}")
    except Exception as e:
        raise SlackAPIError(f"Network or HTTP error: {str(e)}")


def upload_file_to_slack(
    file_path: str,
    channel_id: str,
    bot_token: str,
    initial_comment: Optional[str] = None,
    title: Optional[str] = None
) -> dict:
    """
    Upload a file to a Slack channel using the Slack SDK.

    Uses the official Slack SDK which handles the new files upload workflow automatically.

    Args:
        file_path (str): Path to the file to upload.
        channel_id (str): Slack channel ID where the file will be posted.
        bot_token (str): Slack bot token.
        initial_comment (str, optional): Message to post with the file.
        title (str, optional): Title of the file. If not provided, uses filename.

    Returns:
        dict: Slack API response containing file information.

    Raises:
        SlackAPIError: If Slack API returns error.
        FileNotFoundError: If file does not exist.
    """
    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Create Slack client
    client = WebClient(token=bot_token)

    try:
        # Use files_upload_v2 which handles the new upload workflow automatically
        response = client.files_upload_v2(
            channel=channel_id,
            file=str(file_path),
            title=title if title else file_path_obj.name,
            initial_comment=initial_comment
        )

        return response.data

    except SdkSlackApiError as e:
        raise SlackAPIError(f"Slack API error: {e.response['error']}")
    except Exception as e:
        raise SlackAPIError(f"Unexpected error: {str(e)}")