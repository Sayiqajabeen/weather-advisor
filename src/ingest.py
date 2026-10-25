from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import EMBEDDING_MODEL, KNOWLEDGE_BASE_DIR, VECTORSTORE_DIR


def load_documents():
    """Load all .md files from the knowledge base folder."""
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        raise ValueError(f"No .md files found in {KNOWLEDGE_BASE_DIR}")
    return docs


def split_documents(docs):
    """Split documents into small overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n## ", "\n# ", "\n\n", "\n", " "],
    )
    return splitter.split_documents(docs)


def build_vectorstore(embeddings=None):
    """Build the FAISS index, save it, and return it.

    Pass an existing `embeddings` object to avoid loading the model twice.
    """
    print("Loading documents...")
    docs = load_documents()
    print(f"  Loaded {len(docs)} files")

    print("Splitting into chunks...")
    chunks = split_documents(docs)
    print(f"  Created {len(chunks)} chunks")

    if embeddings is None:
        print("Loading embedding model (first run downloads it, please wait)...")
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    Path(VECTORSTORE_DIR).mkdir(exist_ok=True)
    vectorstore.save_local(VECTORSTORE_DIR)
    print(f"Done. Index saved to '{VECTORSTORE_DIR}/'")
    return vectorstore


if __name__ == "__main__":
    build_vectorstore()