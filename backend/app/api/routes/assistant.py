import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.api.deps import get_current_membership
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember
from app.schemas.assistant import ChatRequest, ChatResponse
from app.api.routes.dashboard import get_summary

# Attempt to import google-genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat_with_assistant(
    business_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    if not HAS_GENAI:
        return ChatResponse(
            response="Error: The google-genai library is not installed."
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ChatResponse(
            response="I am the Mercura AI Assistant. However, the GEMINI_API_KEY is not configured in the backend environment, so I am running in offline mode."
        )

    # Fetch dashboard summary to provide context
    try:
        summary = get_summary(business_id=business_id, db=db, membership=membership)
        context_data = summary.model_dump_json(indent=2)
    except Exception as e:
        context_data = f"Error fetching dashboard summary: {str(e)}"

    system_instruction = (
        "You are the Mercura AI Business Assistant. You help small business owners analyze their operations, "
        "understand their sales data, and manage their inventory. "
        "Be concise, professional, and helpful. "
        f"Here is the current real-time dashboard summary for the user's business:\n{context_data}\n"
        "Use this data to accurately answer questions about their revenue, customers, products, and invoices."
    )

    try:
        client = genai.Client(api_key=api_key)
        
        # Format conversation history
        contents = []
        for msg in request.messages:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
            
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
        return ChatResponse(response=response.text or "I could not generate a response.")
        
    except Exception as e:
        return ChatResponse(
            response=f"An error occurred while communicating with the AI model: {str(e)}"
        )
