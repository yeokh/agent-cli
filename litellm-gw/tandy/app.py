import os
import uuid
import json
from typing import Optional, Union, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, EmailStr
import openai

app = FastAPI(title="Mock Tandem API Service")

# Initialize OpenAI Client (expects OPENAI_API_KEY environment variable or direct pass)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-openai-api-key-here"))

# Model Mapping: Tandem Keys -> OpenAI Model Identifiers
MODEL_MAP = {
    "gpt4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini",
    "gpt41": "gpt-4.1",
    "gpt41-mini": "gpt-4.1-mini",
    "gpt5": "gpt-5",
    "gpt5-mini": "gpt-5-mini",
    "gpto3": "o3",
    "gpto3-mini": "o3-mini",
}

# --- Request Payload Schema ---
class TandemRequest(BaseModel):
    userId: EmailStr = Field(..., description="Mandatory organization email address.")
    message: str = Field(..., description="The user prompt.")
    sessionId: Optional[str] = Field(default=None, description="Session ID for chat memory context.")
    chat_model: Optional[str] = Field(default="gpt4o-mini", description="Selected chat model key.")
    override_chatprompt: Optional[str] = Field(default=None, description="Custom system prompt.")

    temperature: Optional[float] = Field(default=0.0, ge=0.0, le=2.0)
    # Change default to None so we can tell if the user explicitly provided it
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)

    max_token: Optional[int] = Field(default=None, ge=1, le=128000)
    streaming: Optional[Union[bool, str]] = Field(default="true", description="Streaming flag: 'true' or 'false'.")
    
    # Excluded features accepted in payload to maintain API parity without processing logic
    func_bypass: Optional[Union[str, List[str]]] = None
    is_embedding: Optional[bool] = False
    searchindex: Optional[str] = None
    num_search_sources: Optional[int] = 3

# --- Helper Functions ---
def parse_bool(value: Union[bool, str]) -> bool:
    """Normalizes boolean inputs sent as strings or booleans."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")

def map_model(chat_model_key: str) -> str:
    """Maps Tandem model keys to official OpenAI model names."""
    return MODEL_MAP.get(chat_model_key, chat_model_key)

def build_openai_messages(request: TandemRequest) -> List[Dict[str, str]]:
    """Constructs the OpenAI messages array from Tandem parameters."""
    messages = []
    
    # 1. System Prompt (use override_chatprompt if provided, else default fallback)
    system_prompt = request.override_chatprompt or "You are a helpful AI assistant."
    messages.append({"role": "system", "content": system_prompt})
    
    # 2. User Prompt
    messages.append({"role": "user", "content": request.message})
    
    return messages


# --- Endpoint Implementation ---
# List of models that lock temperature to default / do not support custom values
REASONING_MODELS = {"gpt-5", "gpt-5-mini", "gpt5", "gpt5-mini", "o1", "o1-mini", "o3", "o3-mini", "gpto3", "gpto3-mini"}

@app.post("/TandemApi")
async def tandem_api_endpoint(
    payload: TandemRequest,
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Header(None, alias="APIKey"),
    timestamp: Optional[str] = Header(None, alias="Timestamp")
):

    try:
        openai_model = map_model(payload.chat_model)
        messages = build_openai_messages(payload)
        is_stream = parse_bool(payload.streaming)

        # Set up parameters for OpenAI Chat Completion call
        kwargs: Dict[str, Any] = {
            "model": openai_model,
            "messages": messages,
            "stream": is_stream
        }

        # Only include temperature if model is NOT a reasoning model
        if payload.chat_model not in REASONING_MODELS and openai_model not in REASONING_MODELS:
            kwargs["temperature"] = payload.temperature

        if payload.max_token:
            kwargs["max_tokens"] = payload.max_token

        message_id = str(uuid.uuid4())

        # --- STREAMING RESPONSE ---
        if is_stream:
            def stream_generator():
                stream_response = client.chat.completions.create(**kwargs)
                for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        
                        # Formats chunk matching Tandem streaming wrapper structure
                        chunk_payload = {
                            "results": {
                                "chat_model": payload.chat_model,
                                "injected_chatprompt": payload.override_chatprompt,
                                "message": payload.message,
                                "message_id": message_id,
                                "response": content_chunk,
                                "session_id": payload.sessionId,
                                "user_id": payload.userId
                            }
                        }
                        yield f"data: {json.dumps(chunk_payload)}\n\n"

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        # --- NON-STREAMING RESPONSE ---
        else:
            completion = client.chat.completions.create(**kwargs)
            generated_text = completion.choices[0].message.content or ""
            total_tokens = completion.usage.total_tokens if completion.usage else 0

            # Construct Tandem-compliant non-streaming response body
            response_body = {
                "results": {
                    "chat_model": payload.chat_model,
                    "chat_tokens": total_tokens,
                    "injected_chatprompt": payload.override_chatprompt,
                    "message": payload.message,
                    "message_id": message_id,
                    "response": generated_text,
                    "session_id": payload.sessionId,
                    "user_id": payload.userId
                }
            }
            return JSONResponse(content=response_body, status_code=200)

    except openai.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Gateway Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


