import openai
import pinecone
import boto3
import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import time
from typing import Iterator
import concurrent.futures

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document as LCDocument
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

# Load environment variables from .env file
load_dotenv(dotenv_path='/Users/aniketpatole/Documents/GitHub/New/Projects/BigData/Final-Project/.env')

# Initialize OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Pinecone API by creating an instance of Pinecone class
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# S3 bucket name for embeddings and original documents
AWS_BUCKET_VECTORS = os.getenv('AWS_BUCKET_VECTORS')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

# Index names for each category
sporting_index_name = "sporting-regulations-embeddings"
technical_index_name = "technical-regulations-embeddings"
financial_index_name = "financial-regulations-embeddings"
related_index_name = "related-regulations-embeddings"


# Function to create indexes if they don't exist
def create_index_if_not_exists(index_name, dimension=1536):
    """Creates a Pinecone index if it doesn't already exist."""
    print(f"Checking if index {index_name} exists...")
    if index_name not in [idx.name for idx in pinecone_client.list_indexes()]:
        pinecone_client.create_index(
            name=index_name,
            dimension=dimension,
            metric='euclidean',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
        print(f"Index {index_name} created.")
    else:
        print(f"Index {index_name} already exists.")

# Create indexes for each category
create_index_if_not_exists(sporting_index_name)
create_index_if_not_exists(technical_index_name)
create_index_if_not_exists(financial_index_name)
create_index_if_not_exists(related_index_name)

# Loader for PDFs using Docling
class DoclingPDFLoader(BaseLoader):

    def __init__(self, file_path: str | list[str]) -> None:
        self._file_paths = file_path if isinstance(file_path, list) else [file_path]
        self._converter = DocumentConverter()

    def lazy_load(self) -> Iterator[LCDocument]:
        for source in self._file_paths:
            dl_doc = self._converter.convert(source).document
            text = dl_doc.export_to_markdown()
            yield LCDocument(page_content=text)


# Function to extract text using Docling
def extract_text_from_pdf_docling(file_path):
    """Extract text from a PDF document using Docling."""
    loader = DoclingPDFLoader(file_path=file_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    return splits

# Function to fetch documents from S3
def fetch_documents_from_s3(prefix=""):
    """Fetches PDF documents from S3 under the specified prefix."""
    print(f"Fetching documents from S3 with prefix: {prefix}...")
    try:
        response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME, Prefix=prefix)
    except Exception as e:
        print(f"Error fetching documents from S3: {e}")
        return []

    if 'Contents' not in response:
        print(f"No documents found in S3 with prefix: {prefix}.")
        return []

    documents = [{'id': obj['Key'], 's3_key': obj['Key']} for obj in response.get('Contents', []) if obj['Key'].endswith('.pdf')]
    print(f"Fetched {len(documents)} documents from {prefix}.")
    return documents

# Function to generate embeddings using HuggingFace's model
def generate_embedding(text, model_name="BAAI/bge-small-en-v1.5"):
    """Generate embeddings for a given text using HuggingFace's model."""
    print("Generating embedding for the text...")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    embedding = embeddings.embed_query(text)
    print("Embedding generated successfully!")
    return embedding

# Function to save embeddings to Pinecone and S3
def save_embedding_to_pinecone_and_s3(embeddings_batch, regulation_ids, category):
    """Generate embeddings and save them to both Pinecone and S3."""
    try:
        index_map = {
            'sporting': sporting_index_name,
            'technical': technical_index_name,
            'financial': financial_index_name,
            'related_regulations': related_index_name
        }

        if category not in index_map:
            print(f"Invalid category: {category}")
            return

        index = pinecone_client.Index(index_map[category])

        # Upsert the embeddings to Pinecone
        upsert_data = []
        for embedding, regulation_id in zip(embeddings_batch, regulation_ids):
            metadata = {"regulation_id": regulation_id, "s3_key": f"{category}/{regulation_id}.txt"}
            upsert_data.append((regulation_id, embedding, metadata))

        print(f"Upserting batch to Pinecone - Metadata: {metadata}")
        response = index.upsert(upsert_data)
        print(f"Upsert response: {response}")

        # Save the embeddings to S3 as .txt files with metadata
        for embedding, regulation_id in zip(embeddings_batch, regulation_ids):
            embedding_text = json.dumps({"embedding": embedding, "metadata": metadata})
            s3_client.put_object(
                Bucket=AWS_BUCKET_VECTORS,
                Key=f"{category}/{regulation_id}.txt",
                Body=embedding_text
            )

        print(f"Embeddings saved to {category} in Pinecone and S3.")
    except Exception as e:
        print(f"Error saving batch to Pinecone or S3: {e}")

# Function to process each regulation document
def process_regulation_document(document):
    regulation_id = document['id']
    s3_key = document['s3_key']
    category = regulation_id.split("/")[0]  # Assuming category is part of the folder structure in the S3 key

    try:
        print(f"Extracting text from {regulation_id} using Docling...")
        file_path = f"/tmp/{os.path.basename(s3_key)}"
        s3_client.download_file(AWS_BUCKET_NAME, s3_key, file_path)
        splits = extract_text_from_pdf_docling(file_path)

        if splits:
            print(f"Text extracted for {regulation_id}...")
            # Process in batch
            batch_size = 10
            for i in range(0, len(splits), batch_size):
                batch_splits = splits[i:i + batch_size]
                batch_texts = [split.page_content for split in batch_splits]
                regulation_ids = [f"{regulation_id}_chunk_{i+j+1}" for j in range(len(batch_splits))]

                print("Generating embeddings for the batch...")
                embeddings_batch = [generate_embedding(text) for text in batch_texts]
                print("Embeddings generated successfully for the batch!")

                save_embedding_to_pinecone_and_s3(embeddings_batch, regulation_ids, category)

            print(f"Completed processing for {regulation_id}.")
        else:
            print(f"Failed to extract text for {regulation_id}")
    except Exception as e:
        print(f"Error processing document {regulation_id}: {e}")

# Function to process all documents in parallel
def process_all_documents():
    categories = ['sporting', 'technical', 'financial', 'related_regulations']
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_doc = {}
        for category in categories:
            documents = fetch_documents_from_s3(prefix=f"{category}/")
            for document in documents:
                future = executor.submit(process_regulation_document, document)
                future_to_doc[future] = document

        for future in concurrent.futures.as_completed(future_to_doc):
            document = future_to_doc[future]
            try:
                future.result()
            except Exception as e:
                print(f"Document {document['id']} generated an exception: {e}")

# Run the function locally
if __name__ == "__main__":
    print("Starting document processing...")
    process_all_documents()
