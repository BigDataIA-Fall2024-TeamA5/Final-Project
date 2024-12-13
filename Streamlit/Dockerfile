# Use an official Python base image
FROM python:3.12-slim

# Use Bash as the default shell
SHELL ["/bin/bash", "-c"]

# Set the working directory
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
RUN poetry install --no-dev --no-root

# Verify Streamlit is installed
RUN poetry run streamlit --version

# Expose the Streamlit port
EXPOSE 8501

# Run the Streamlit app
CMD ["poetry", "run", "streamlit", "run", "Streamlit/main.py", "--server.port", "8501"]