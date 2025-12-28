from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import rag
import shutil
from pathlib import Path

app = FastAPI(
    title="Document Intelligence API",
    description="RAG-based API for querying documents (PDF, CSV, DOCX, TXT)",
    version="2.0.0"
)

# CORS middleware for chatbot UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary storage for uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class QueryRequest(BaseModel):
    query: str

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the key findings in the report?"
            }
        }


class QueryResponse(BaseModel):
    answer: str
    sources: str
    confidence: Optional[str] = None


class ProcessResponse(BaseModel):
    message: str
    files_processed: int
    chunks_created: int
    status: str


class ChatMessage(BaseModel):
    """For chatbot UI compatibility"""
    message: str
    conversation_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Summarize the quarterly sales report",
                "conversation_id": "user-123-session-456"
            }
        }


class ChatResponse(BaseModel):
    """Chatbot-compatible response format"""
    reply: str
    sources: List[str]
    conversation_id: Optional[str] = None


@app.get("/")
async def root():
    return {
        "service": "Document Intelligence API",
        "version": "2.0.0",
        "status": "active",
        "capabilities": [
            "PDF processing",
            "CSV/Excel analysis",
            "DOCX document parsing",
            "Multi-document querying",
            "Chatbot integration"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    vector_store_ready = rag.vector_store is not None
    llm_ready = rag.llm is not None

    return {
        "status": "healthy",
        "vector_store": "ready" if vector_store_ready else "not initialized",
        "llm": "ready" if llm_ready else "not initialized"
    }


@app.post("/v1/upload-documents", response_model=ProcessResponse)
async def upload_documents(
        files: List[UploadFile] = File(..., description="Upload PDF, CSV, DOCX, or TXT files")
):
    """
    Upload and process documents into the knowledge base.
    Supports: PDF, CSV, XLSX, DOCX, TXT
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file types
    allowed_extensions = {".pdf", ".csv", ".xlsx", ".docx", ".txt"}
    uploaded_paths = []

    try:
        for file in files:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
                )

            # Save uploaded file
            file_path = UPLOAD_DIR / file.filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_paths.append(str(file_path))

        # Process documents through RAG pipeline
        status_messages = []
        for message in rag.process_documents(uploaded_paths):
            status_messages.append(message)
            print(f"Processing: {message}")

        # Extract final status
        final_status = status_messages[-1] if status_messages else "Processing completed"

        # Extract chunk count from final message
        chunks_created = 0
        if "chunks" in final_status.lower():
            try:
                chunks_created = int([s for s in final_status.split() if s.isdigit()][0])
            except:
                pass

        return ProcessResponse(
            message="Documents processed successfully",
            files_processed=len(files),
            chunks_created=chunks_created,
            status=final_status
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Cleanup uploaded files
        for path in uploaded_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except:
                pass


@app.post("/v1/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the knowledge base with natural language questions.
    Returns answers grounded in uploaded documents.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        answer, sources = rag.generate_answer(request.query)

        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence="high" if sources and "No sources" not in sources else "low"
        )

    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.post("/v1/chat", response_model=ChatResponse)
async def chat_interface(message: ChatMessage):
    """
    Chatbot-compatible endpoint for UI integration.
    Maintains conversation context through conversation_id.
    """
    if not message.message or not message.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        answer, sources = rag.generate_answer(message.message)

        # Parse sources into list format for chatbot UI
        source_list = []
        if sources and "No sources" not in sources:
            source_list = [s.strip("- ").strip() for s in sources.split("\n") if s.strip()]

        return ChatResponse(
            reply=answer,
            sources=source_list,
            conversation_id=message.conversation_id
        )

    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.delete("/v1/reset")
async def reset_knowledge_base():
    """
    Clear all documents from the knowledge base.
    Use with caution in production environments.
    """
    try:
        if rag.vector_store:
            rag.vector_store.reset_collection()
            return {
                "message": "Knowledge base cleared successfully",
                "status": "reset_complete"
            }
        else:
            return {
                "message": "No knowledge base to reset",
                "status": "not_initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")


@app.get("/v1/stats")
async def get_statistics():
    """
    Get current knowledge base statistics.
    """
    try:
        if rag.vector_store:
            count = rag.vector_store._collection.count()
            return {
                "total_chunks": count,
                "status": "initialized" if count > 0 else "empty",
                "embedding_model": rag.EMBEDDING_MODEL,
                "llm_model": "llama-3.3-70b-versatile"
            }
        else:
            return {
                "total_chunks": 0,
                "status": "not_initialized"
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)