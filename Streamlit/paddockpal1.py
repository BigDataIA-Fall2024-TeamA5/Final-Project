import os
import openai
from pinecone import Pinecone, ServerlessSpec
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API key setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENV")

# Validate environment variables
if not OPENAI_API_KEY or not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
    raise ValueError("API keys or environment variables for OpenAI and Pinecone are missing.")

# Initialize Pinecone using the new class-based method
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

# Ensure Pinecone indexes exist
INDEX_NAMES = [
    "sporting-regulations-embeddings",
    "technical-regulations-embeddings",
    "financial-regulations-embeddings",
]

INDEX_HOSTS = {
    "sporting-regulations-embeddings": "sporting-regulations-embeddings-jl357j9.svc.aped-4627-b74a.pinecone.io",
    "technical-regulations-embeddings": "technical-regulations-embeddings-jl357j9.svc.aped-4627-b74a.pinecone.io",
    "financial-regulations-embeddings": "financial-regulations-embeddings-jl357j9.svc.aped-4627-b74a.pinecone.io",
}

def ensure_index_exists(index_name, dimension=1536, metric="cosine"):
    """
    Ensure that the specified Pinecone index exists. If it does not exist, create it.
    """
    if index_name not in pinecone_client.list_indexes().names():
        pinecone_client.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )
        print(f"Created index: {index_name}")
    else:
        print(f"Index {index_name} already exists.")

# Ensure all indexes exist
for index in INDEX_NAMES:
    ensure_index_exists(index)

def get_pinecone_index(index_name):
    """
    Retrieve a Pinecone index by name using the correct host.
    """
    if not PINECONE_ENVIRONMENT:
        raise ValueError("PINECONE_ENVIRONMENT is not set. Ensure it is defined in the environment variables.")
    
    host = INDEX_HOSTS.get(index_name)
    if not host:
        raise ValueError(f"Host for index {index_name} is not defined.")
    
    print(f"Connecting to Pinecone index at host: {host}")
    return pinecone_client.Index(index_name, host=host)

# OpenAI API key setup
openai.api_key = OPENAI_API_KEY

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

def query_pinecone(index_name, query_embedding, keywords=None, top_k=5):
    """
    Perform a hybrid search combining semantic search and keyword-based filtering.
    """
    if keywords is None:
        keywords = []

    try:
        index = get_pinecone_index(index_name)
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        matches = response.get("matches", [])

        # Keyword-based filtering
        keyword_matches = [
            match for match in matches
            if any(keyword.lower() in match["metadata"].get("text", "").lower() for keyword in keywords)
        ]

        # Combine results with priority for keyword matches
        combined_results = keyword_matches + [m for m in matches if m not in keyword_matches]
        return combined_results[:top_k]
    except Exception as e:
        print(f"Error querying index {index_name}: {e}")
        return []

def fetch_relevant_documents(query):
    print(f"Processing query: {query}")
    query_embedding = generate_embeddings_openai(query)
    if not query_embedding:
        print("Failed to generate query embeddings.")
        return []

    all_results = []
    for index_name in INDEX_NAMES:
        print(f"Searching index: {index_name}...")
        results = query_pinecone(index_name, query_embedding, keywords=[], top_k=10)
        print(f"Results from {index_name}: {results}")
        all_results.extend(results)

    sorted_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_results[:5]

def get_combined_context(matches):
    seen_texts = set()
    contexts = []
    for match in matches:
        text = match["metadata"].get("text", "")
        if text and text not in seen_texts:
            seen_texts.add(text)
            contexts.append(text)
    return "\n\n".join(contexts[:3])

def generate_answer_with_openai(context, query):
    if not context:
        return "No relevant information found in the database."

    messages = [
        {"role": "system", "content": "You are a knowledgeable assistant with expertise in Formula 1 regulations."},
        {"role": "user", "content": f"""Based on the following context, answer the question in detail. Provide a comprehensive response, include all relevant points, and elaborate wherever possible.

Context:
{context}

Question:
{query}"""}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=5000,
            temperature=0.7,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error generating answer with OpenAI: {e}")
        return "An error occurred while generating the answer."

def main():
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

        print(answer)
        print("\n" + "=" * 50)

def show_paddockpal():
    st.write("Ask questions about Formula 1 regulations and get accurate answers!")

    query = st.text_input("Enter your question:", key="user_query")
    if st.button("Submit"):
        if not query.strip():
            st.warning("Please enter a valid question.")
        else:
            st.write("Processing your query...")
            matches = fetch_relevant_documents(query)
            context = get_combined_context(matches)

            st.subheader("Generated Answer:")
            answer = generate_answer_with_openai(context, query)
            st.write(answer)

if __name__ == "__main__":
    main()