import requests
from ..config import settings
from typing import Dict

def post_escalation_to_slack(original_query: str, llm_analysis: str, on_call_team: str, sources: list):
    """
    Formats and posts a detailed escalation message to a specified Slack channel.
    """
    slack_token = settings.SLACK_BOT_TOKEN
    channel_id = settings.SLACK_ESCALATION_CHANNEL_ID

    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    # --- Build a rich message using Slack's Block Kit ---
    
    # Extract the most relevant source for context
    most_relevant_source = sources[0]['document'] if sources else "No specific past incident found."

    # Create Slack blocks for a well-formatted message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 New Issue Escalation",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"A new issue has been raised and requires attention from *{on_call_team}*."
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*User's Query:*\n> {original_query}"
                }
            ]
        },
        {
			"type": "divider"
		},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Analysis & Suggested Next Steps:*\n{llm_analysis}"
            }
        },
        {
			"type": "divider"
		},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Most Relevant Past Incident for Context:*\n```{most_relevant_source}```"
                }
            ]
        }
    ]

    payload = {
        "channel": channel_id,
        "blocks": blocks,
        "text": f"New Escalation: {original_query}" # Fallback text for notifications
    }

    try:
        response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("ok"):
            print(f"✅ Successfully posted escalation to channel {channel_id}.")
            return {"status": "success", "message": "Posted to Slack."}
        else:
            print(f"❌ Failed to post to Slack: {response_data.get('error')}")
            return {"status": "error", "message": response_data.get('error')}
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while posting to Slack: {e}")
        return {"status": "error", "message": str(e)}


def post_escalation_to_slack_v2(llm_json_response: Dict, original_query: str):
    """
    Posts a pre-formatted Block Kit JSON message to a specified Slack channel.
    """
    slack_token = settings.SLACK_BOT_TOKEN
    channel_id = settings.SLACK_ESCALATION_CHANNEL_ID
    headers = {"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json; charset=utf-8"}

    # Extract the 'blocks' from the LLM's JSON response
    blocks_to_post = llm_json_response.get("blocks", [])

    if not blocks_to_post:
        print("❌ LLM response contained no blocks to post.")
        return {"status": "error", "message": "No blocks found in LLM response."}

    payload = {
        "channel": channel_id,
        "blocks": blocks_to_post,
        "text": f"Synapse AI Analysis for: {original_query}" # Fallback for notifications
    }

    try:
        response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("ok"):
            print(f"✅ Successfully posted Block Kit message to channel {channel_id}.")
            return {"status": "success"}
        else:
            error_msg = response_data.get('error')
            print(f"❌ Failed to post to Slack: {error_msg}")
            return {"status": "error", "message": error_msg}
    except Exception as e:
        print(f"❌ Network error while posting to Slack: {e}")
        return {"status": "error", "message": str(e)}