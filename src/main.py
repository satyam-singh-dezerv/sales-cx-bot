# src/main.py
from fastapi import FastAPI, HTTPException
from .models import ExtractionRequest, ExtractionResponse, QueryRequest, QueryResponse
# from .services.slack_extractor import extract_channel_knowledge
from .services.slack_extractor import extract_and_store_knowledge
from pydantic import BaseModel
from .services.knowledge_store import KnowledgeStore
from .services.llm_handler import generate_answer, generate_answer_v2 # <-- Import the new function
from fastapi.middleware.cors import CORSMiddleware # Import the middleware
from .services.slack_poster import post_escalation_to_slack, post_escalation_to_slack_v2


app = FastAPI(
    title="Knowledge Base Extractor API",
    description="An API to extract conversational knowledge from Slack channels and enrich it with Jira data.",
    version="1.0.0"
)

class ExtractionStatusResponse(BaseModel):
    status: str
    threads_processed: int
    message: str
# This defines the list of "origins" (frontends) that are allowed to talk to your API.
origins = [
    "http://localhost",
    "http://localhost:8080", # If you serve your frontend with `python -m http.server 8080`
    "http://127.0.0.1:8080",
    "null" # Allow requests from `file:///` origins (like opening index.html directly)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Allow specific origins
    # You can also use `allow_origins=["*"]` to allow all origins during development
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)


@app.post("/api/v1/extract", response_model=ExtractionStatusResponse)
async def run_extraction(request: ExtractionRequest):
    """
    Triggers the extraction process for a given Slack channel.
    This is a long-running process and may time out on serverless platforms.
    """
    try:
        print(f"Starting extraction for channel: {request.channel_id}")
        # Run the blocking I/O operation in a thread pool to avoid blocking the event loop
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            extract_and_store_knowledge,
            request.channel_id,
            request.months_history
        )

        return result
    except Exception as e:
        # Catch-all for unexpected errors during the process
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred: {str(e)}"
        )

@app.post("/api/v1/query", response_model=QueryResponse)
def query_knowledge_base(request: QueryRequest):
    """
    Performs the full RAG pipeline: retrieves context and generates an answer.
    """
    try:
        # 1. Retrieve (The part that's already working)
        store = KnowledgeStore()
        search_results = store.query_knowledge(
            query_text=request.query, 
            n_results=request.top_k
        )

        if not search_results or not search_results.get('documents') or not search_results['documents'][0]:
             return QueryResponse(answer="I couldn't find any relevant information in the knowledge base.", sources=[])
        
        # 2. Generate (The new step)
        answer = generate_answer(request.query, search_results.get('documents', []))

        # print(answer)
        import re
        # 3. Respond
        # We can format the sources for better readability
        sources = [
            {
                "document": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(search_results['documents'][0], search_results['metadatas'][0], search_results['distances'][0])
        ]
    
        on_call_team_match = re.search(r'@[\w-]+', answer)
        on_call_team = on_call_team_match.group(0) if on_call_team_match else "@on-call-team" # Fallback
        
        post_escalation_to_slack(
            original_query=request.query,
            llm_analysis=answer,
            on_call_team=on_call_team,
            sources=sources
        )

        return QueryResponse(answer=answer, sources=sources)
        
    except Exception as e:
        print(f"An unexpected error occurred during query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v2/query", response_model=QueryResponse)
def query_knowledge_base(request: QueryRequest):
    """
    Performs RAG, generates a Slack Block Kit message, posts it automatically,
    and returns a text summary to the caller.
    """
    try:
        # 1. Retrieve context
        store = KnowledgeStore()
        search_results = store.query_knowledge(
            query_text=request.query, 
            n_results=request.top_k
        )

        if not search_results or not search_results.get('documents') or not search_results['documents'][0]:
             return QueryResponse(answer="I couldn't find any relevant information in the knowledge base.", sources=[])
        
        # 2. Generate the Block Kit JSON from the LLM
        # The 'answer_json' variable will be a dictionary like {"blocks": [...]}
        answer_json = generate_answer_v2(request.query, search_results.get('documents', []))

        print(answer_json)

        # 3. Post the rich message directly to Slack
        post_escalation_to_slack_v2(
            llm_json_response=answer_json,
            original_query=request.query
        )

        # 4. Create a simple text summary for the API response
        # This joins the text from all the 'section' blocks for a clean summary.
        summary_text = "\n\n".join(
            block.get("text", {}).get("text", "")
            for block in answer_json.get("blocks", [])
            if block.get("type") == "section"
        ).strip()
        
        if not summary_text:
            summary_text = "Analysis was posted to Slack, but a text summary could not be generated."

        # 5. Format sources and return the final response
        sources = [
            {
                "document": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(search_results['documents'][0], search_results['metadatas'][0], search_results['distances'][0])
        ]

        return QueryResponse(answer=summary_text, sources=sources)
        
    except Exception as e:
        print(f"An unexpected error occurred during query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")