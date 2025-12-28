from uuid import uuid4
from dotenv import load_dotenv
from pathlib import Path
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    Docx2txtLoader,
    TextLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
import warnings

warnings.filterwarnings('ignore')

load_dotenv()

# Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTORSTORE_DIR = Path(__file__).parent / "resources" / "vectorstore"
COLLECTION_NAME = "documents_kb"

llm = None
vector_store = None


def initialize_components():
    """Initialize LLM and vector store"""
    global llm, vector_store

    if llm is None:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1000
        )

    if vector_store is None:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"trust_remote_code": True}
        )

        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_DIR)
        )


def load_document(file_path: str):
    """
    Load document based on file extension.
    Supports: PDF, CSV, XLSX, DOCX, TXT
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    try:
        if extension == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif extension == ".csv":
            loader = CSVLoader(str(file_path))
        elif extension == ".xlsx":
            loader = UnstructuredExcelLoader(str(file_path), mode="elements")
        elif extension == ".docx":
            loader = Docx2txtLoader(str(file_path))
        elif extension == ".txt":
            loader = TextLoader(str(file_path))
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        documents = loader.load()

        # Add filename to metadata
        for doc in documents:
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            doc.metadata['source'] = file_path.name
            doc.metadata['file_type'] = extension

        return documents

    except Exception as e:
        raise Exception(f"Error loading {file_path.name}: {str(e)}")


def process_documents(file_paths: List[str]):
    """
    Process multiple documents into vector store.
    Generator function that yields progress messages.
    """
    yield "Initializing AI components..."
    initialize_components()

    yield "Clearing previous knowledge base..."
    vector_store.reset_collection()

    all_documents = []

    yield f"Loading {len(file_paths)} document(s)..."

    for file_path in file_paths:
        try:
            docs = load_document(file_path)
            all_documents.extend(docs)
            yield f"✓ Loaded {Path(file_path).name} ({len(docs)} sections)"
        except Exception as e:
            yield f"✗ Failed to load {Path(file_path).name}: {str(e)}"
            continue

    if not all_documents:
        yield "✗ No documents loaded successfully"
        return

    total_chars = sum(len(doc.page_content) for doc in all_documents)
    yield f"✓ Total content loaded: {total_chars:,} characters"

    yield "Splitting documents into semantic chunks..."
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )

    chunks = splitter.split_documents(all_documents)

    if not chunks:
        yield "✗ Failed to create text chunks"
        return

    yield f"✓ Created {len(chunks)} chunks"

    yield "Generating embeddings and storing in vector database..."
    try:
        ids = [str(uuid4()) for _ in chunks]
        vector_store.add_documents(documents=chunks, ids=ids)

        # Verify storage
        count = vector_store._collection.count()
        yield f"✓ SUCCESS! Knowledge base ready with {count} chunks"

    except Exception as e:
        yield f"✗ Storage error: {str(e)}"


def generate_answer(query: str):
    """
    Generate answer from knowledge base.
    Returns (answer, sources) tuple.
    """
    if vector_store is None:
        raise RuntimeError("Knowledge base not initialized. Upload documents first.")

    # Check vector store status
    try:
        count = vector_store._collection.count()
        print(f"DEBUG: Vector store has {count} chunks")

        if count == 0:
            return (
                "Knowledge base is empty. Please upload documents first.",
                ""
            )
    except Exception as e:
        print(f"DEBUG: Error checking collection: {e}")

    # Retrieve relevant documents
    try:
        docs_with_scores = vector_store.similarity_search_with_score(query, k=6)

        print(f"DEBUG: Retrieved {len(docs_with_scores)} documents")
        for i, (doc, score) in enumerate(docs_with_scores[:3]):
            print(f"DEBUG: Doc {i + 1} - Score: {score:.4f} - Source: {doc.metadata.get('source', 'unknown')}")

        if not docs_with_scores:
            return (
                "No relevant information found for your query. Try rephrasing or upload more documents.",
                ""
            )

        # Filter by relevance
        relevant_docs = [doc for doc, score in docs_with_scores if score < 2.5]

        if not relevant_docs:
            print("DEBUG: Using top results despite score threshold")
            relevant_docs = [doc for doc, _ in docs_with_scores[:4]]

    except Exception as e:
        print(f"DEBUG: Retrieval error: {e}")
        return (f"Error searching knowledge base: {str(e)}", "")

    # Build context
    context_parts = []
    sources = set()

    for i, doc in enumerate(relevant_docs[:5], 1):
        source_name = doc.metadata.get('source', 'Unknown')
        file_type = doc.metadata.get('file_type', '')

        context_parts.append(f"[Document {i}: {source_name}]\n{doc.page_content}\n")
        sources.add(f"{source_name} ({file_type})" if file_type else source_name)

    context = "\n".join(context_parts)

    # Generate answer
    prompt = f"""You are an intelligent document assistant. Answer the question using ONLY the information from the provided documents.

DOCUMENTS:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Provide a clear, detailed answer based solely on the document content
- If the documents contain the information, give a comprehensive response
- Include specific details, numbers, or facts from the documents when relevant
- If the information is not in the documents, clearly state: "This information is not available in the uploaded documents"
- Do not make assumptions or add information not present in the documents
- If multiple documents discuss the topic, synthesize the information

ANSWER:"""

    try:
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)

        # Format sources
        formatted_sources = "\n".join([f"- {src}" for src in sorted(sources)])

        return (answer.strip(), formatted_sources)

    except Exception as e:
        print(f"DEBUG: LLM error: {e}")
        return (f"Error generating answer: {str(e)}", "")