import os
from dotenv import load_dotenv
from pinecone import Pinecone
import openai
import streamlit as st
import requests


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


def query_pinecone(index_name, query_embedding, keywords, top_k=5):
    """
    Perform a hybrid search combining semantic search and keyword-based filtering.
    """
    try:
        index = pinecone_client.Index(index_name)
        # Semantic search using query embedding
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


def expand_query(query):
    """
    Generate alternative phrasings for the query using OpenAI Chat API.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in rephrasing queries."},
                {"role": "user", "content": f"Generate alternative phrasings for the query: '{query}'"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        expansions = response["choices"][0]["message"]["content"].split("\n")
        return [q.strip() for q in expansions if q.strip()]
    except Exception as e:
        print(f"Error generating query expansions: {e}")
        return [query]

def fetch_relevant_documents(query):
    print("Generating embedding for the query using OpenAI...")
    query_embedding = generate_embeddings_openai(query)
    if not query_embedding:
        print("Failed to generate query embeddings.")
        return []

    all_results = []
    for index_name in INDEX_NAMES:
        print(f"Searching index: {index_name}...")
        # Pass an empty list for keywords if none are being used
        results = query_pinecone(index_name, query_embedding, keywords=[], top_k=10)  
        for match in results:
            print(f"Match: {match['metadata'].get('text', '')[:100]}... (Score: {match.get('score', 0)})")
        all_results.extend(results)

    # Sort results by score in descending order
    sorted_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_results[:5]

def get_combined_context(matches):
    """
    Combine text metadata from the top matches into a single context,
    while filtering duplicates.
    """
    seen_texts = set()
    contexts = []
    for match in matches:
        text = match["metadata"].get("text", "")
        if text and text not in seen_texts:
            seen_texts.add(text)
            contexts.append(text)
    return "\n\n".join(contexts[:3])  # Combine top 3 unique matches

def generate_answer_with_openai(context, query):
    """
    Generate an answer for the query using OpenAI GPT-4 (Chat API), based on the given context.
    """
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
            max_tokens=5000,  # Increase the token limit
            temperature=0.7,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error generating answer with OpenAI: {e}")
        return "An error occurred while generating the answer."

"""
def main():

    Main entry point for the F1 Regulations Assistant.

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

        print("This is the context from the embeddings:")
        print(context)
        print("\nThis is the Answer:")
        print(answer)
        print("\n" + "="*50)
"""

def show_paddockpal():
    st.title("Paddock Pal Bot")
    st.write("Ask questions about Formula 1 regulations and get accurate answers!")

    # Input section for user queries
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
