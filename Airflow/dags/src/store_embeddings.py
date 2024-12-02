import openai
import pinecone
import boto3
import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import time

# Load environment variables from .env file
load_dotenv(dotenv_path='/Users/aniketpatole/Documents/GitHub/New/Projects/BigData/Final-Project/.env')

# Initialize OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Pinecone API by creating an instance of Pinecone class
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize S3 and Textract clients
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

textract_client = boto3.client('textract')

# S3 bucket name for embeddings and original documents
AWS_BUCKET_VECTORS = os.getenv('AWS_BUCKET_VECTORS')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

# Index names for each category
sporting_index_name = "sporting-regulations-embeddings"
technical_index_name = "technical-regulations-embeddings"
financial_index_name = "financial-regulations-embeddings"
related_index_name = 'related-regulations-embeddings'


# Function to create indexes if they don't exist
def create_index_if_not_exists(index_name, dimension=1536):
    """Creates a Pinecone index if it doesn't already exist."""
    print(f"Checking if index {index_name} exists...")
    if index_name not in pinecone_client.list_indexes().names():
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


# Function to generate embeddings using OpenAI's model
def generate_embedding(text):
    """Generate embeddings for a given text using OpenAI's API."""
    print("Generating embedding for the text...")
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    print("Embedding generated successfully!")
    return response.data[0].embedding


# Function to chunk the text into large chunks
def chunk_text(text, chunk_size=2000):
    """Chunks the text into smaller pieces of a given size."""
    print(f"Splitting text of length {len(text)} into chunks of size {chunk_size}...")
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    print(f"Created {len(chunks)} chunks.")
    return chunks


# Function to start document text detection using Textract
def extract_text_from_pdf_textract(s3_key):
    """Extract text from a PDF document stored in S3 using Textract."""
    print(f"Starting text detection for {s3_key}...")
    response = textract_client.start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': AWS_BUCKET_NAME, 'Name': s3_key}}
    )
    job_id = response['JobId']
    print(f"Started text detection job with Job ID: {job_id}")

    # Poll for job completion
    while True:
        result = textract_client.get_document_text_detection(JobId=job_id)
        status = result['JobStatus']
        if status in ['SUCCEEDED', 'FAILED']:
            break
        print(f"Job status: {status}, waiting for 5 seconds...")
        time.sleep(5)

    # Extract text from the result
    if status == 'SUCCEEDED':
        text = '\n'.join([block['Text'] for block in result['Blocks'] if block['BlockType'] == 'LINE'])
        print(f"Text extracted for {s3_key}.")
        return text
    else:
        print(f"Text extraction failed for {s3_key} with status: {status}.")
        return None


# Function to upload PDF chunks to S3
def upload_chunks_to_s3(chunks, regulation_id, category):
    """Uploads the text chunks to S3 and returns their keys."""
    print(f"Uploading {len(chunks)} chunks to S3 under {category}/{regulation_id}...")
    s3_keys = []
    for idx, chunk in enumerate(chunks):
        # Fix the S3 key generation to avoid nested directories
        chunk_key = f"{category}/{regulation_id}_chunk_{idx + 1}.txt"
        s3_client.put_object(Bucket=AWS_BUCKET_VECTORS, Key=chunk_key, Body=chunk)
        s3_keys.append(chunk_key)
    print(f"Chunks uploaded to S3 with keys: {s3_keys}")
    return s3_keys

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


# Function to save embeddings to Pinecone and S3
def save_embedding_to_pinecone_and_s3(text, regulation_id, category):
    """Generate embeddings and save them to both Pinecone and S3."""
    try:
        print(f"Generating embedding for regulation {regulation_id}...")
        embedding = generate_embedding(text)
        print(f"Generated embedding for regulation {regulation_id}.")

        metadata = {"regulation_id": regulation_id, "s3_key": f"{category}/{regulation_id}.txt"}

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

        # Upsert the embedding to Pinecone
        print(f"Upserting to Pinecone - ID: {regulation_id}, Metadata: {metadata}, Embedding: {embedding[:10]}...")
        response = index.upsert([(regulation_id, embedding, metadata)])
        print(f"Upsert response: {response}")

        # Save the embedding to S3 as a .txt file with metadata
        embedding_text = json.dumps({"embedding": embedding, "metadata": metadata})
        s3_client.put_object(
            Bucket=AWS_BUCKET_VECTORS,
            Key=f"{category}/{regulation_id}.txt",
            Body=embedding_text
        )

        print(f"Embedding for regulation {regulation_id} saved to {category} in Pinecone and S3.")
    except Exception as e:
        print(f"Error saving embedding for regulation {regulation_id}: {e}")


# Function to process each regulation document
def process_regulation_document(document):
    regulation_id = document['id']
    s3_key = document['s3_key']
    category = regulation_id.split("/")[0]  # Assuming category is part of the folder structure in the S3 key

    print(f"Extracting text from {regulation_id}...")
    text = extract_text_from_pdf_textract(s3_key)

    if text:
        print(f"Text extracted for {regulation_id}...")
        chunks = chunk_text(text, chunk_size=2000)
        print(f"Text split into {len(chunks)} chunks for {regulation_id}...")

        # Upload chunks to S3
        s3_keys = upload_chunks_to_s3(chunks, regulation_id, category)

        # Process each chunk and create embeddings
        for chunk, chunk_key in zip(chunks, s3_keys):
            print(f"Creating embeddings for chunk of {regulation_id}...")
            save_embedding_to_pinecone_and_s3(chunk, f"{regulation_id}_chunk", category)

        print(f"Completed processing for {regulation_id}.")
    else:
        print(f"Failed to extract text for {regulation_id}")


# Function to process all documents sequentially
def process_all_documents():
    categories = ['sporting', 'technical', 'financial']
    
    for category in categories:
        documents = fetch_documents_from_s3(prefix=f"{category}/")
        print(f"Fetched {len(documents)} documents from {category}.")

        for document in documents:
            process_regulation_document(document)


# Run the function locally
if __name__ == "__main__":
    print("Starting document processing...")
    process_all_documents()