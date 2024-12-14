# Paddock Pal

## Drive Through F1 Knowledge

## Overview
Paddock Pal is an intelligent assistant designed to provide detailed and accurate information about Formula 1 regulations. Leveraging the power of OpenAI and Pinecone, Paddock Pal offers users a seamless way to query and explore sporting, technical, and financial regulations.

## Features
- **Embeddings and Search**: Combines semantic and keyword-based search for precise results.
- **F1 Knowledge base: Knowledge base for those who are new to formula 1. Data Scrapped from wikipedia and openf1 api.
- **Multi-Agentic Architecture**: Handles Reflective architecture for regulation categories: sporting, technical, and financial.
- **User-Friendly Interface**: Built with Streamlit for a clean and intuitive user experience.

## Technologies Used
- **Python**: Core programming language.
- **Streamlit**: Frontend framework for interactive web applications.
- **OpenAI**: For generating embeddings and GPT-4-powered answers.
- **Pinecone**: For storing and querying vector embeddings.
- **dotenv**: For managing environment variables securely.

## Architecture Diagram

## Project Structure
```
Final-Project/
├── .github/
│   └── workflows/
│       ├── fastapi_deployment.yml
│       ├── streamlit_deployment.yml
├── Airflow/
│   ├── dags/
│   ├── logs/
│   ├── plugins/
│   ├── airflow.cfg
│   ├── airflow.db
│   ├── docker-compose.yaml
│   ├── Dockerfile
│   └── requirements.txt
├── FastAPI/
│   ├── __init__.py
│   ├── Dockerfile
│   ├── jwtauth.py
│   ├── main.py
│   ├── poetry.lock
│   └── pyproject.toml
├── Streamlit/
│   ├── Images/
│   ├── __init__.py
│   ├── Dockerfile
│   ├── informationpage.py
│   ├── landing.py
│   ├── main.py
│   ├── paddockpal1.py
│   ├── tracks_drivers.py
│   ├── poetry.lock
│   ├── pyproject.toml
│   └── README.md
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
├── LICENSE
└── README.md
```

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/PaddockPal.git
   cd PaddockPal
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   python -m venv f1env
   source f1env/bin/activate  # On Windows: f1env\Scripts\activate
   ```

3. **Install Required Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the `Streamlit/` directory with the following variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=us-east-1
   ```

5. **Run the Application**
   ```bash
   cd Streamlit
   streamlit run main.py
   ```

## Usage
1. Navigate to the local URL provided by Streamlit.
2. Enter your query in the input box (e.g., "What are the financial regulations of 2026?").
3. Click the "Submit" button to view results.

## Key Components
### 1. **`scrape_to_s3.py`**
   - Handles AWS and Pinecone connections.
   - Ensures indexes exist in Pinecone.

### 2. **`paddockpal.py`**
   - Core logic for embedding generation, querying Pinecone, and fetching results.
   - Combines semantic and keyword-based search for relevant answers.

### 3. **`landing.py`**
   - Defines the landing page and app structure for Streamlit.

### 4. **`main.py`**
   - Entry point for the Streamlit application.
   - Connects user inputs to backend logic.

## Example Queries
- "What are the technical regulations for the 2026 season?"
- "Explain the financial regulations in Formula 1."
- "What changes were made to sporting regulations in 2024?"

## Troubleshooting
1. **Environment Variable Errors**:
   Ensure all required keys are set in the `.env` file.

2. **Pinecone Connection Issues**:
   - Verify the `PINECONE_API_KEY` and `PINECONE_ENVIRONMENT` values.
   - Check the Pinecone dashboard for index statuses.

3. **Streamlit Errors**:
   Ensure Streamlit is installed and all dependencies are satisfied.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Contact
For queries or support, please contact:
- **Email**: patole.an@northeastern.edu, vyawahare.s@northeastern.edu, bage.s@northeastern.edu
