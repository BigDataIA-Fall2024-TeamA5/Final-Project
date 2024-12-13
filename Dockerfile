# Use an official Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files into the container
COPY . .

# Install dependencies using Poetry
RUN poetry install --no-dev

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Run FastAPI and Streamlit
CMD ["sh", "-c", "uvicorn FastAPI.main:app --host 0.0.0.0 --port 8000 & streamlit run Streamlit/main.py --server.port 8501"]