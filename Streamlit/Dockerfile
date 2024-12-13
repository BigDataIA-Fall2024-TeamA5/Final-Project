# Use an official Python base image
FROM python:3.12-slim

# Set Bash as the default shell
SHELL ["/bin/bash", "-c"]

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

# Copy project files
COPY . .

# Install dependencies using Poetry
RUN poetry install --no-root --only main

# Verify that Streamlit is installed
RUN poetry run streamlit --version

# Expose the Streamlit port
EXPOSE 8501

# Default command to run the Streamlit app
CMD ["poetry", "run", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]