# src/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ExtractionRequest(BaseModel):
    """Defines the request body for the extraction endpoint."""
    channel_id: str = Field(
        ...,
        description="The Slack Channel ID to extract knowledge from (e.g., C08UEHGQLA1)."
    )
    months_history: int = Field(
        default=3,
        gt=0,
        le=12,
        description="The number of months of history to fetch (1-12)."
    )

class ExtractionResponse(BaseModel):
    """Defines the successful response structure."""
    status: str = "success"
    channel_id: str
    thread_count: int
    data: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question.")
    top_k: int = Field(3, description="Number of results to return for context.")

# NEW: A clean response model for the final answer
class QueryResponse(BaseModel):
    answer: str
    # escalation_message: str
    sources: List[Dict]