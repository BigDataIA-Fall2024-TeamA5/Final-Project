# Use the slim Python 3.12 image as the base
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Poetry
RUN pip install poetry

# Copy dependency files into the container
COPY pyproject.toml poetry.lock ./

# Install only main dependencies using Poetry
RUN poetry install --no-root --only main

# Copy the application code into the container
COPY . .

# Install uvicorn explicitly as it’s used in CMD
RUN pip install uvicorn

# Expose the port used by the FastAPI application
EXPOSE 8000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]