# src/services/jira_enricher.py
import requests
import re
from functools import lru_cache
from ..config import settings

# --- Jira Helper Functions ---

def _parse_adf_text(adf_node):
    """Recursively parses Jira's Atlassian Document Format (ADF) to extract plain text."""
    if not adf_node or not isinstance(adf_node, dict): return ""
    text_content = ""
    if adf_node.get("type") == "text":
        text_content += adf_node.get("text", "")
    if "content" in adf_node and isinstance(adf_node["content"], list):
        for child_node in adf_node["content"]:
            text_content += _parse_adf_text(child_node)
    return text_content.strip()

@lru_cache(maxsize=128) # Cache results for recently fetched tickets
def fetch_jira_ticket_details(ticket_id: str):
    """Fetches ticket summary, description, and comments from the Jira API."""
    if not all([settings.JIRA_BASE_URL, settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN]):
        return None

    try:
        url = f"{settings.JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{ticket_id}?fields=summary,description,comment"
        auth = requests.auth.HTTPBasicAuth(settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN)
        headers = {"Accept": "application/json"}
        
        resp = requests.get(url, headers=headers, auth=auth, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        fields = data.get("fields", {})
        
        description = _parse_adf_text(fields.get("description"))
        
        comments_data = []
        if fields.get("comment", {}).get("comments"):
            for comment in fields["comment"]["comments"]:
                comments_data.append({
                    "author": comment.get("author", {}).get("displayName", "Unknown"),
                    "created": comment.get("created"),
                    "body": _parse_adf_text(comment.get("body"))
                })
        
        return {
            "summary": fields.get("summary"),
            "description": description,
            "comments": comments_data
        }
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching Jira ticket {ticket_id}: {e}")
        return None