# Document Intelligence API

Production-grade RAG API for intelligent document querying. Upload PDFs, spreadsheets, Word documents, or text files and ask natural language questions. Designed for chatbot integration and internal knowledge base systems.

## Overview

This API transforms unstructured documents into a queryable knowledge base using Retrieval-Augmented Generation (RAG). All answers are strictly grounded in your uploaded documents, preventing hallucinations and ensuring factual accuracy.

**Primary Use Cases:**
- Internal company chatbots
- Document Q&A systems
- Report analysis and summarization
- Knowledge base creation from corporate documents
- Automated information extraction from files

## Key Features

- **Multi-Format Support:** PDF, CSV, Excel, DOCX, TXT
- **Intelligent Chunking:** Semantic text splitting with context preservation
- **Source Citation:** Every answer includes document references
- **Chatbot Ready:** Dedicated `/v1/chat` endpoint for UI integration
- **CORS Enabled:** Ready for frontend chatbot interfaces
- **Stateful Storage:** Persistent vector database across sessions
- **RESTful Design:** Standard HTTP endpoints with OpenAPI documentation

## Architecture

### Processing Pipeline

1. **Document Upload:** Multi-file upload via HTTP POST
2. **Content Extraction:** Format-specific loaders for each file type
3. **Text Chunking:** Recursive splitting with overlap for context
4. **Embedding Generation:** HuggingFace sentence transformers
5. **Vector Storage:** ChromaDB with persistent disk storage

### Query Pipeline

1. **User Question:** Natural language query via API
2. **Semantic Search:** Vector similarity across document chunks
3. **Context Retrieval:** Top-k relevant passages with scores
4. **Answer Generation:** LLM-powered response with grounding
5. **Source Attribution:** File names and metadata returned

### Technology Stack

- **API:** FastAPI with automatic Swagger UI
- **LLM:** Groq (LLaMA 3.3 70B Versatile)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2
- **Vector DB:** ChromaDB (persistent storage)
- **Document Loaders:** LangChain community loaders
- **Orchestration:** LangChain for RAG workflow

## API Endpoints

### Core Endpoints

#### Upload Documents
```http
POST /v1/upload-documents
Content-Type: multipart/form-data
```

Upload one or more documents to build the knowledge base.

**Request:**
```bash
curl -X POST "http://localhost:8000/v1/upload-documents" \
  -F "files=@quarterly_report.pdf" \
  -F "files=@sales_data.xlsx" \
  -F "files=@product_specs.docx"
```

**Response:**
```json
{
  "message": "Documents processed successfully",
  "files_processed": 3,
  "chunks_created": 47,
  "status": "SUCCESS! Knowledge base ready with 47 chunks"
}
```

#### Query Documents
```http
POST /v1/query
Content-Type: application/json
```

Ask questions about uploaded documents.

**Request:**
```json
{
  "query": "What were the Q3 sales figures?"
}
```

**Response:**
```json
{
  "answer": "According to the quarterly report, Q3 sales reached $2.4M, representing a 15% increase from Q2...",
  "sources": "- quarterly_report.pdf (.pdf)\n- sales_data.xlsx (.xlsx)",
  "confidence": "high"
}
```

#### Chat Interface (Chatbot Compatible)
```http
POST /v1/chat
Content-Type: application/json
```

Chatbot-optimized endpoint with conversation tracking.

**Request:**
```json
{
  "message": "Summarize the main findings",
  "conversation_id": "user-123-session-456"
}
```

**Response:**
```json
{
  "reply": "The main findings indicate...",
  "sources": [
    "quarterly_report.pdf (.pdf)",
    "sales_data.xlsx (.xlsx)"
  ],
  "conversation_id": "user-123-session-456"
}
```

### Utility Endpoints

#### Statistics
```http
GET /v1/stats
```

Get knowledge base statistics.

```json
{
  "total_chunks": 47,
  "status": "initialized",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "llm_model": "llama-3.3-70b-versatile"
}
```

#### Reset Knowledge Base
```http
DELETE /v1/reset
```

Clear all documents from the knowledge base.

#### Health Check
```http
GET /health
```

## Installation

### Prerequisites

- Python 3.10+
- pip package manager
- Groq API key (free tier available)

### Quick Start

1. **Clone and setup:**
```bash
git clone <repository-url>
cd document-intelligence-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
echo "GROQ_API_KEY=your_api_key_here" > .env
```

4. **Run server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

5. **Access Swagger UI:**
```
http://localhost:8000/docs
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for LLM access | Yes |

### Model Configuration (`rag.py`)

```python
CHUNK_SIZE = 1000           # Characters per chunk
CHUNK_OVERLAP = 200         # Overlap between chunks
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "documents_kb"
```

## Usage Examples

### Python Client

```python
import requests

# Upload documents
with open('report.pdf', 'rb') as f:
    files = {'files': f}
    response = requests.post(
        'http://localhost:8000/v1/upload-documents',
        files=files
    )
    print(response.json())

# Query
response = requests.post(
    'http://localhost:8000/v1/query',
    json={'query': 'What is the revenue?'}
)
print(response.json()['answer'])
```

### JavaScript/TypeScript

```javascript
// Upload documents
const formData = new FormData();
formData.append('files', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8000/v1/upload-documents', {
  method: 'POST',
  body: formData
});

// Query
const queryResponse = await fetch('http://localhost:8000/v1/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'Summarize key points' })
});

const data = await queryResponse.json();
console.log(data.answer);
```

### Chatbot Integration Example

```javascript
async function sendChatMessage(message, conversationId) {
  const response = await fetch('http://localhost:8000/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      conversation_id: conversationId
    })
  });
  
  const data = await response.json();
  return {
    reply: data.reply,
    sources: data.sources,
    conversationId: data.conversation_id
  };
}
```

## Project Structure

```
.
├── main.py                    # FastAPI routes and endpoints
├── rag.py                     # RAG processing engine
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (git-ignored)
├── .gitignore                # Git exclusions
├── uploads/                   # Temporary file storage (auto-created)
├── resources/
│   └── vectorstore/          # Persistent ChromaDB storage
└── README.md                 # This file
```

## Deployment

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p uploads resources/vectorstore

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
docker build -t doc-intelligence-api .
docker run -p 8000:8000 -v $(pwd)/resources:/app/resources --env-file .env doc-intelligence-api
```

### Cloud Deployment

**AWS ECS/Fargate:**
- Use EFS for persistent vector store
- Application Load Balancer for HTTPS
- Environment variables via Secrets Manager

**Azure Container Instances:**
- Azure Files for vector store persistence
- API Management for authentication
- Key Vault for secrets

**Google Cloud Run:**
- Cloud Storage FUSE for persistence
- Cloud Endpoints for API management
- Secret Manager for API keys

### Kubernetes

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vectorstore-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: doc-intelligence-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: doc-intelligence-api:latest
        volumeMounts:
        - name: vectorstore
          mountPath: /app/resources/vectorstore
        env:
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: groq-api-key
      volumes:
      - name: vectorstore
        persistentVolumeClaim:
          claimName: vectorstore-pvc
```

## Chatbot UI Integration

### Recommended Frameworks

- **Streamlit Chat:** Python-based rapid prototyping
- **React Chat UI:** react-chatbot-kit, react-chat-widget
- **Vue Chat:** vue-advanced-chat
- **Custom WebSocket:** For real-time streaming responses

### Integration Pattern

```javascript
// Frontend chatbot integration
class DocumentChatbot {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
    this.conversationId = this.generateId();
  }
  
  async sendMessage(message) {
    const response = await fetch(`${this.apiUrl}/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        conversation_id: this.conversationId
      })
    });
    
    return await response.json();
  }
  
  async uploadDocuments(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const response = await fetch(`${this.apiUrl}/v1/upload-documents`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  }
}
```

## Supported File Types

| Format | Extension | Loader | Notes |
|--------|-----------|--------|-------|
| PDF | `.pdf` | PyPDFLoader | Text extraction, supports scanned PDFs with OCR |
| CSV | `.csv` | CSVLoader | Column-based data, automatic header detection |
| Excel | `.xlsx` | UnstructuredExcelLoader | Multiple sheets supported |
| Word | `.docx` | Docx2txtLoader | Text, tables, limited formatting |
| Text | `.txt` | TextLoader | Plain text files |

## Limitations

- **File Size:** Recommended max 50MB per file
- **OCR:** Scanned PDFs require additional setup
- **Tables:** Complex table structures may lose formatting
- **Images:** Text in images not extracted without OCR
- **Memory:** Large documents require adequate RAM
- **Concurrent Uploads:** Single-threaded processing
- **Multi-tenancy:** Shared vector store (isolation required for multi-user)

## Security Considerations

- **Input Validation:** File type and size restrictions enforced
- **CORS:** Configure allowed origins for production
- **API Keys:** Never commit `.env` to version control
- **Authentication:** No built-in auth; use API gateway
- **Data Isolation:** Single knowledge base; implement user isolation for multi-tenant
- **File Cleanup:** Uploaded files deleted after processing
- **Prompt Injection:** Safe prompt design mitigates risks

## Performance Optimization

- **Batch Processing:** Process multiple documents in single upload
- **Chunk Size Tuning:** Adjust based on document type
- **Embedding Cache:** HuggingFace model caching enabled
- **Vector Store Indexing:** ChromaDB automatic indexing
- **Query Optimization:** Adjust `k` parameter for retrieval

## Troubleshooting

### Common Issues

**"Knowledge base not initialized"**
- Upload documents first before querying

**"No relevant information found"**
- Documents may not contain answer
- Try different phrasing
- Check if documents uploaded successfully

**"Unsupported file type"**
- Verify file extension matches supported formats
- Check file is not corrupted

**Low confidence answers**
- Upload more relevant documents
- Increase chunk overlap
- Adjust similarity threshold

## Future Enhancements

- Streaming responses for real-time chat experience
- Multi-tenant support with user-isolated vector stores
- Advanced OCR for scanned documents
- Table extraction and structured data querying
- Multi-language support
- Document version management
- Conversation memory and context tracking
- Custom embedding models
- Fine-tuned LLMs for domain-specific tasks
- Rate limiting and quota management
- Webhook notifications for processing completion
- Bulk document processing with job queue

## License

Provided for demonstration and development. For production deployment, ensure compliance with:
- Groq API Terms of Service
- HuggingFace Model Licenses
- Document content copyright and usage rights
- Data privacy regulations (GDPR, CCPA, HIPAA if applicable)

## Support

For issues or questions:
- Check `/docs` endpoint for API documentation
- Review debug logs in console output
- Contact development team for enterprise support

---

**Version:** 2.0.0  
**Last Updated:** December 2025  
**Status:** Production Ready