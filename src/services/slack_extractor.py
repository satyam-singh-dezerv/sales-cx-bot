import requests
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..config import settings
from .jira_enricher import fetch_jira_ticket_details
from .knowledge_store import KnowledgeStore


# --- Caching (Module-level for a single worker process) ---
user_cache = {}
usergroup_cache = {}

# --- Slack Helper Functions ---

def _get_user_name(user_id: str, headers: Dict) -> str:
    """Fetches a user's real name from their ID, using a cache."""
    if not user_id:
        return "Unknown"
    if user_id in user_cache:
        return user_cache[user_id]
    try:
        resp = requests.get("https://slack.com/api/users.info", headers=headers, params={"user": user_id})
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            name = data["user"].get("real_name") or data["user"].get("name", user_id)
            user_cache[user_id] = name
            return name
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user {user_id}: {e}")
    return user_id

def _load_usergroups(headers: Dict):
    """Loads all usergroups into a cache for mention resolution."""
    if usergroup_cache:
        return
    try:
        resp = requests.get("https://slack.com/api/usergroups.list", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            for g in data.get("usergroups", []):
                usergroup_cache[g["id"]] = g["handle"]
    except requests.exceptions.RequestException as e:
        print(f"Error loading usergroups: {e}")

def _resolve_mentions(text: str, headers: Dict) -> str:
    """Replaces Slack-specific mention syntax with human-readable names."""
    if not text:
        return ""
    text = re.sub(r"<@([A-Z0-9]+)>", lambda m: "@" + _get_user_name(m.group(1), headers), text)
    text = re.sub(r"<!subteam\^([A-Z0-9]+)(?:\|([^>]+))?>", lambda m: "@" + (usergroup_cache.get(m.group(1), m.group(2) or m.group(1))), text)
    return text.replace("<!here>", "@here").replace("<!channel>", "@channel").replace("<!everyone>", "@everyone")

def _extract_links(text: str) -> List[Dict]:
    """Finds and classifies URLs within a message text."""
    if not text:
        return []
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    classified_links = []
    for url in urls:
        link_type = "other"
        if "docs.google.com" in url:
            link_type = "google_doc"
        elif "atlassian.net/wiki" in url or "confluence" in url:
            link_type = "confluence"
        elif "jira" in url or "atlassian.net/browse" in url:
            link_type = "jira"
        classified_links.append({"url": url, "type": link_type})
    return classified_links

def _process_message(msg: Dict, headers: Dict, is_reply: bool = False) -> Optional[Dict]:
    """Processes a single message, extracting all relevant data."""
    if "subtype" in msg and msg["subtype"] not in ["file_share", "thread_broadcast"]:
        return None

    text_content = _resolve_mentions(msg.get("text", ""), headers)
    
    # Use a more specific regex to avoid false positives
    ticket_ids = re.findall(r'\b([A-Z]{2,6}-\d{1,6})\b', text_content)
    jira_tickets = []
    for ticket_id in set(ticket_ids):
        details = fetch_jira_ticket_details(ticket_id)
        if details:
            jira_tickets.append({"ticket_id": ticket_id, **details})
            
    files = [{"id": f.get("id"), "name": f.get("name")} for f in msg.get("files", [])]

    return {
        "ts": msg["ts"],
        "datetime_utc": datetime.utcfromtimestamp(float(msg["ts"])).isoformat(),
        "user": _get_user_name(msg.get("user"), headers),
        "text": text_content,
        "links": _extract_links(text_content),
        "jira_tickets": jira_tickets,
        "files": files,
        "is_thread_reply": is_reply,
        "reply_count": msg.get("reply_count", 0),
        "replies": []
    }

def _fetch_paginated_data(api_method: str, params: Dict, headers: Dict) -> List[Dict]:
    """Generic function to fetch paginated data from a Slack API."""
    all_items = []
    cursor = None
    while True:
        try:
            request_params = {**params, "limit": 200}
            if cursor:
                request_params["cursor"] = cursor
            
            resp = requests.get(f"https://slack.com/api/{api_method}", headers=headers, params=request_params)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                error = data.get("error", "unknown")
                if error == "ratelimited":
                    retry_after = int(resp.headers.get("Retry-After", "20"))
                    print(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                raise Exception(f"Error from {api_method}: {error}")
            
            all_items.extend(data.get("messages", []))
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            time.sleep(1.2)
        except requests.exceptions.RequestException as e:
            print(f"Network error during fetch: {e}")
            break
    return all_items

# --- Main Export Logic ---

def extract_and_store_knowledge(channel_id: str, months_history: int) -> dict:
    """
    Main function to export a channel's history, including all thread replies,
    and store it in the vector database.
    """
    headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
    knowledge_store = KnowledgeStore()
    
    print("Loading usergroups...")
    _load_usergroups(headers)
    
    oldest_ts = (datetime.now() - timedelta(days=months_history * 30)).timestamp()
    
    print(f"Fetching parent messages for channel {channel_id}...")
    parent_messages = _fetch_paginated_data(
        "conversations.history", 
        {"channel": channel_id, "oldest": oldest_ts}, 
        headers
    )
    
    threads_processed = 0
    print(f"Found {len(parent_messages)} total messages. Processing threads...")
    for parent_msg_data in parent_messages:
        # Skip messages that are replies themselves; we'll fetch them under their parent.
        if parent_msg_data.get("thread_ts") and parent_msg_data.get("ts") != parent_msg_data.get("thread_ts"):
            continue

        thread_obj = _process_message(parent_msg_data, headers, is_reply=False)
        if not thread_obj:
            continue
            
        # If the parent message has replies, fetch them in a separate, dedicated API call.
        if thread_obj['reply_count'] > 0:
            print(f"Fetching {thread_obj['reply_count']} replies for thread {thread_obj['ts']}...")
            reply_messages_data = _fetch_paginated_data(
                "conversations.replies",
                {"channel": channel_id, "ts": thread_obj['ts']},
                headers
            )
            
            # The first message in the replies API is the parent itself, so we skip it.
            for reply_msg_data in reply_messages_data[1:]:
                processed_reply = _process_message(reply_msg_data, headers, is_reply=True)
                if processed_reply:
                    thread_obj['replies'].append(processed_reply)
        
        # Now that the thread object is complete, store it.
        knowledge_store.add_thread(thread_obj)
        threads_processed += 1
    
    return {
        "status": "success",
        "threads_processed": threads_processed,
        "message": "Knowledge base updated successfully."
    }