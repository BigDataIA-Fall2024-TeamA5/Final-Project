import os
import openai
from pinecone import Pinecone, ServerlessSpec
import streamlit as st
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# OpenAI and Pinecone API setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENV")
NEWS_API_KEY = os.getenv("NEWSAPI_API_KEY")  # Add your NewsAPI key to .env

# Validate environment variables
if not OPENAI_API_KEY or not PINECONE_API_KEY or not PINECONE_ENVIRONMENT or not NEWS_API_KEY:
    raise ValueError("API keys or environment variables for OpenAI, Pinecone, or NewsAPI are missing.")

# Initialize Pinecone client
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

# Ensure Pinecone indexes exist
def ensure_index_exists(index_name, dimension=1536, metric="cosine"):
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

for index in INDEX_NAMES:
    ensure_index_exists(index)

def get_pinecone_index(index_name):
    host = INDEX_HOSTS.get(index_name)
    if not host:
        raise ValueError(f"Host for index {index_name} is not defined.")
    return pinecone_client.Index(index_name, host=host)

# OpenAI setup
openai.api_key = OPENAI_API_KEY

def generate_embeddings_openai(text):
    try:
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response["data"][0]["embedding"]
    except Exception as e:
        print(f"Error generating embeddings with OpenAI: {e}")
        return None

def fetch_f1_news():
    """Fetch strictly F1-related news articles from NewsAPI."""
    url = f"https://newsapi.org/v2/everything?q=\"Formula 1\" OR F1&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            # Filter further if necessary to ensure relevance
            filtered_articles = [
                article for article in articles
                if "formula" in article["title"].lower() or "f1" in article["title"].lower()
            ]
            return filtered_articles
        else:
            st.error(f"Error fetching news: {response.json().get('message')}")
            return []
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []

def display_news_section():
    """Display a news section with hover effects and dynamic article details."""
    st.markdown(
        """
        <style>
        .news-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            padding: 20px;
        }
        .news-card {
            flex: 0 1 calc(33.333% - 20px);
            min-width: 300px;
            position: relative;
            overflow: hidden;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            background: white;
            transition: transform 0.3s ease;
        }
        .news-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 15px 15px 0 0;
        }
        .news-card:hover {
            transform: translateY(-5px);
        }
        .news-content {
            padding: 15px;
        }
        .news-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .news-description {
            font-size: 14px;
            color: #666;
            margin-bottom: 15px;
            line-height: 1.4;
        }
        .read-more {
            display: inline-block;
            padding: 8px 16px;
            background-color: #E10600;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s ease;
        }
        .read-more:hover {
            background-color: #B30500;
        }
        @media (max-width: 992px) {
            .news-card {
                flex: 0 1 calc(50% - 20px);
            }
        }
        @media (max-width: 768px) {
            .news-card {
                flex: 0 1 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    articles = fetch_f1_news()

    if articles:
        st.markdown('<div class="news-container">', unsafe_allow_html=True)
        for article in articles[:9]:
            image = article.get("urlToImage", "")
            title = article.get("title", "No Title")
            description = article.get("description", "No description available.")
            url = article.get("url", "#")

            st.markdown(
                f"""
                <div class="news-card">
                    <img src="{image}" alt="{title}">
                    <div class="news-content">
                        <div class="news-title">{title}</div>
                        <div class="news-description">{description}</div>
                        <a href="{url}" target="_blank" class="read-more">Read More</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No news articles available at the moment.")

# Main function
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

    # Display F1 News Section
    display_news_section()

if __name__ == "__main__":
    show_paddockpal()
