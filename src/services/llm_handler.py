# src/services/llm_handler.py

import google.generativeai as genai # CHANGED: Import Google's library
from typing import List, Dict
from ..config import settings
from .slack_extractor import usergroup_cache, _load_usergroups
from datetime import datetime
import json
from .slack_extractor import usergroup_cache
# CHANGED: Configure the Gemini client with the API key
genai.configure(api_key=settings.GOOGLE_API_KEY)

if not usergroup_cache:
    headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
    _load_usergroups(headers)



# def generate_answer(question: str, context: List[Dict]):
#     """
#     Uses Google's Gemini model to generate an answer based on the provided context.
#     """
#     # print(context)
#     context_documents = context
#     current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     user_name = "John Doe"
#     prompt = f"""
# **## System Prompt: Synapse, Expert Support Analyst**

# **### Core Identity & Objective**
# You are **"Synapse,"** an expert-level Support Analyst AI. Your objective is to help team members diagnose new technical problems by providing a structured analysis of relevant past incidents from a knowledge base. You are analytical, clear, and your goal is to empower the user to solve their own problem.

# **### Crucial Constraints**
# -   You **MUST** base your entire analysis strictly on the provided `context_documents`. If the context is insufficient, state that and provide only general troubleshooting steps.
# -   You **MUST NOT** invent information or provide a definitive "final answer." Use guiding language (e.g., "A possible cause could be...").
# -   You **MUST** adhere to all markdown formatting rules for clarity.

# ---

# **## Dynamic Inputs**
# * `{question}`: The user's description of their current problem.
# * `{context_documents}`: A collection of relevant past incident summaries.
# * `{usergroup_cache}`: A JSON object mapping keywords to on-call groups (e.g., `{"lead": "@crm-oncall", "transaction": "@transact-oncall"}`).
# * `{user_name}`: The name of the user asking the question.
# * `{escalation_channel_id}`: The Slack channel ID for escalations.

# ---

# **## Core Task for Synapse**

# Hi {user_name}, I've received your query. Here is my analysis based on past incidents.

# **User's Current Problem:**
# "{question}"

# **Relevant Knowledge Base Articles:**
# ---
# {context_documents}
# ---

# **### Step-by-Step Instructions for Your Analysis:**

# 1.  **Deconstruct the Query:** First, analyze the `{question}` to identify the core system, error messages, and user's intent.

# 2.  **Synthesize Potential Causes:** Scan the `{context_documents}` for matching patterns. Based on the most relevant incidents, create a bulleted list of potential root causes. Generalize specific details into broader categories (e.g., "Data Sync Error," "Insufficient Account Permissions").

# 3.  **Present a Case Study:** Select the single most relevant incident from the context. If multiple incidents show a clear pattern, you may reference them. Summarize it with the following structure:
#     * **`### Case Study: [Brief Title of Incident]`**
#     * **Situation:** Describe the past problem.
#     * **Resolution:** State how it was resolved and which teams were involved.

# 4.  **Formulate Actionable Next Steps:** Create a numbered list of clear, diagnostic actions the user should take.
#     * **First Step - Tag the Right Team:** Your very first step **must** be to identify the correct on-call team. To do this, find keywords from the `{question}` in the `{usergroup_cache}` and suggest tagging the corresponding team.
#     * **Subsequent Steps:** Derive the next steps from the successful troubleshooting paths seen in the `context_documents`.

# 5.  **Provide Escalation Option:** As the final part of your response, generate a pre-formatted message that the user can copy and paste into the `<#{escalation_channel_id}>` channel. This message should tag the on-call team you identified in the previous step and briefly state the user's problem.

# **Begin your response now, starting with a brief acknowledgment of the user's problem.**
# """

#     try:
#         # CHANGED: Select the Gemini model and call it
#         # 'gemini-1.5-flash-latest' is fast and very capable.
#         model = genai.GenerativeModel('gemini-1.5-flash-latest')
#         response = model.generate_content(prompt)
        
#         # CHANGED: Access the generated text
#         answer = response.text
#         return answer
#     except Exception as e:
#         print(f"Error calling Google API: {e}")
#         return "Sorry, I encountered an error while generating the answer."


def generate_answer(question: str, context: List[Dict], user_name: str = "Team Member"):
    """
    Uses Google's Gemini model to generate an answer based on the provided context.
    """
    
    context_documents = context
    
    # A placeholder for your usergroup cache logic
    usergroup_cache = {
        "lead": "@crm-oncall",
        "transaction": "@transact-oncall",
        "pms": "@pms-ops-support",
        "portfolio": "@portfolio-reviews-oncall",
        "dividend": "@portfolio-reviews-oncall",
        "deck": "@portfolio-reviews-oncall"
    }

    # REMOVED the 'f' prefix and ESCAPED the literal braces with {{ and }}
    prompt = """
**## System Prompt: Synapse, Expert Support Analyst**

**### Core Identity & Objective**
You are **"Synapse,"** an expert-level Support Analyst AI. Your objective is to help team members diagnose new technical problems by providing a structured analysis of relevant past incidents from a knowledge base. You are analytical, clear, and your goal is to empower the user to solve their own problem.

**### Crucial Constraints**
-   You **MUST** base your entire analysis strictly on the provided `context_documents`. If the context is insufficient, state that and provide only general troubleshooting steps.
-   You **MUST NOT** invent information or provide a definitive "final answer." Use guiding language (e.g., "A possible cause could be...").
-   You **MUST** adhere to all markdown formatting rules for clarity.

---

**## Dynamic Inputs**
* `{{question}}`: The user's description of their current problem.
* `{{context_documents}}`: A collection of relevant past incident summaries.
* `{{usergroup_cache}}`: A JSON object mapping keywords to on-call groups (e.g., `{{"lead": "@crm-oncall", "transaction": "@transact-oncall"}}`).
* `{{user_name}}`: The name of the user asking the question.

---

**## Core Task for Synapse**

Hi {user_name}, I've received your query. Here is my analysis based on past incidents.

**User's Current Problem:**
"{question}"

**Relevant Knowledge Base Articles:**
---
{context_documents}
---

**### Your Required Output Structure and Logic:**

1.  **Acknowledge and Reframe:** Start by briefly acknowledging the user's problem to show you've understood.
2.  **Synthesize Potential Causes:** Create a bulleted list of potential causes identified from your analysis.
3.  **Present a Case Study:** Select and summarize the single most relevant incident from the context.
4.  **Identify and State the On-Call Team:** Create a new section with the heading `## Recommended On-Call Team`. In this section, explicitly state the single most relevant on-call team by finding keywords from the `{{question}}` in the `{usergroup_cache}`. For example: "The recommended team to investigate this is **@portfolio-reviews-oncall**." This is a critical step for automated routing.
5.  **Provide Actionable Next Steps:** Create a numbered list of diagnostic actions the user should take. Do **not** include "tag the on-call team" as a step, as this is now handled automatically.

**Begin your response now.**
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Pass the full context to the model using .format()
        full_prompt_with_context = prompt.format(
            question=question,
            context_documents=json.dumps(context_documents, indent=2),
            usergroup_cache=json.dumps(usergroup_cache, indent=2),
            user_name=user_name
        )

        response = model.generate_content(full_prompt_with_context)
        
        return response.text
    except Exception as e:
        print(f"Error calling Google API: {e}")
        return "Sorry, I encountered an error while generating the answer."


def generate_answer_v2(question: str, context: List[Dict], user_name: str = "Team Member"):
    """
    Uses Google's Gemini model to generate a rich Slack Block Kit JSON object,
    which is then parsed into a Python dictionary.
    """
    
    context_documents = context

    print(context_documents)

    for document in context_documents:
        print(document)

    # This is the final, highly-detailed prompt for generating rich, analytical Slack messages.
    # This prompt has the correct structure and brace escaping.
    prompt_template = """
**Your Task:** You are an AI Support Analyst named Synapse. Your goal is to generate a valid Slack Block Kit JSON object based on the user's question and the provided context of past incidents.

**### CRITICAL Instructions:**

1.  Your entire output **MUST** be a single, valid JSON object with a key `"blocks"`.

2.  **Initial Synthesis (Broad View):** Scan **ALL** `__CONTEXT_DOCUMENTS__` to identify recurring themes. Use this to create a brief, bulleted list for the `💡 Potential Causes` section.

3.  **Focused Analysis (Deep Dive):** Select the **SINGLE** most relevant document from the context. This document will be the "Primary Source" for the rest of your analysis.

4.  **Case Study:** Based *only* on the Primary Source, create a short and concise 150 words`📌 Case Study`.

5.  **On-Call Team Identification:** Analyze the entire conversation of the Primary Source, including replies. Prioritize the team tagged last. This is the **only** team you should state in the `🧑‍💻 Recommended On-Call Team` section. You **MUST** format it as a bolded Slack user group mention (e.g., `*@cx-team*`).

6.  **Actionable Next Steps:** Derive the `➡️ Actionable Next Steps` **directly from the resolution or troubleshooting steps described in your single chosen Case Study**. This ensures the steps are concrete and relevant.

7.  **Cite Sources:** In the `📚 Similar Incidents` section, cite the top 3 most relevant documents by summarizing them in a single, short line each.

8.  **Formatting:** Use emojis (🔍, 💡, 📌, 🧑‍💻, ➡️, 📚) and `mrkdwn` bolding (`*text*`) for all headers. Do not include an "Incident ID" section.




---
**## Data Inputs**

**User's Question:**
__QUESTION__

**Knowledge Base Context (Ranked by Relevance):**
__CONTEXT_DOCUMENTS__

**User Name:** __USER_NAME__

**Usergroup Cache:**
__USERGROUP_CACHE__

**Begin your JSON output now.**
    """

    try:
        # Safely build the prompt using chained .replace() calls.
        full_prompt = (prompt_template
            .replace("__QUESTION__", json.dumps(question, ensure_ascii=False))
            .replace("__CONTEXT_DOCUMENTS__", json.dumps(context_documents, ensure_ascii=False))
            .replace("__USER_NAME__", json.dumps(user_name, ensure_ascii=False))
            .replace("__USERGROUP_CACHE__", json.dumps(usergroup_cache, ensure_ascii=False))
        )
        
        # # --- Crucial Debugging Step ---
        # print("\n--- PROMPT SENT TO GEMINI ---\n")
        # print(full_prompt)
        # print("\n-----------------------------\n")
        # # --------------------------------

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
        
        response_text = model.generate_content(full_prompt).text
        
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()

        return json.loads(response_text)

    except json.JSONDecodeError as e:
        print(f"❌ LLM did not return valid JSON: {e}")
        print(f"Raw response from LLM:\n---\n{response_text}\n---")
        return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Sorry, the AI returned an invalid response. Please check the server logs."}}]}
    except Exception as e:
        print(f"An error occurred during the API call: {e}")
        return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "An unexpected error occurred while generating the analysis."}}]}