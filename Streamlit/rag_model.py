import os
from dotenv import load_dotenv
from pinecone import Pinecone
import openai

# Load environment variables
load_dotenv()

# OpenAI and Pinecone setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENV")

# Validate environment variables
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("API keys for OpenAI or Pinecone are missing.")

# Initialize Pinecone and OpenAI
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
openai.api_key = OPENAI_API_KEY

# Pinecone index names
INDEX_NAMES = [
    "sporting-regulations-embeddings",
    "technical-regulations-embeddings",
    "financial-regulations-embeddings",
    "related-regulations-embeddings",
]

def generate_embeddings_openai(text):
    """
    Generate embeddings for the given text using OpenAI's 'text-embedding-ada-002' model.
    """
    try:
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response["data"][0]["embedding"]
    except Exception as e:
        print(f"Error generating embeddings with OpenAI: {e}")
        return None

def query_pinecone(index_name, query_embedding, top_k=5):
    """
    Query Pinecone for the most relevant documents.
    """
    try:
        index = pinecone_client.Index(index_name)
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return response.get("matches", [])
    except Exception as e:
        print(f"Error querying index {index_name}: {e}")
        return []

def fetch_relevant_documents(query):
    """
    Fetch relevant documents for a given query using OpenAI embeddings and Pinecone.
    """
    print("Generating embedding for the query using OpenAI...")
    query_embedding = generate_embeddings_openai(query)
    if not query_embedding:
        print("Failed to generate query embeddings.")
        return []

    all_results = []
    for index_name in INDEX_NAMES:
        print(f"Searching index: {index_name}...")
        results = query_pinecone(index_name, query_embedding, top_k=5)
        all_results.extend(results)

    # Sort results by score in descending order
    sorted_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_results[:5]

def get_combined_context(matches):
    contexts = [match["metadata"].get("text", "") for match in matches if "text" in match["metadata"]]
    combined_context = "\n\n".join(contexts[:10])  # Use more matches if needed
    return combined_context

def generate_answer_with_openai(context, query):
    """
    Generate an answer for the query using OpenAI GPT-4 (Chat API), based on the given context.
    """
    if not context:
        return "No relevant information found in the database."

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error generating answer with OpenAI: {e}")
        return "An error occurred while generating the answer."

def main():
    """
    Main entry point for the F1 Regulations Assistant.
    """
    print("\n=== F1 Regulations Assistant ===")
    while True:
        query = input("\nEnter your question (type 'exit' to quit): ").strip()
        if query.lower() == "exit":
            print("Exiting F1 Regulations Assistant. Goodbye!")
            break

        print("\nProcessing query...")
        matches = fetch_relevant_documents(query)
        context = get_combined_context(matches)
        answer = generate_answer_with_openai(context, query)
        print("This is the context from the embeddings:-")
        print(context)
        print("\nthis is the Answer:")
        print(answer)
        print("\n" + "="*50)

if __name__ == "__main__":
    main()