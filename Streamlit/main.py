import streamlit as st
import requests
import snowflake.connector
from dotenv import load_dotenv
import os
from PIL import Image
import io
import base64

# Load environment variables
load_dotenv()

# FastAPI endpoint URLs for user login and PDF list retrieval
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
REGISTER_URL = f"{FASTAPI_URL}/auth/register"
LOGIN_URL = f"{FASTAPI_URL}/auth/login"

# Set up Streamlit page configuration with a wide layout
st.set_page_config(page_title="PDF Text Extraction Application", layout="wide")

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None
if 'pdf_data' not in st.session_state:
    st.session_state['pdf_data'] = []
if 'selected_pdf' not in st.session_state:
    st.session_state['selected_pdf'] = None
if 'view_mode' not in st.session_state:
    st.session_state['view_mode'] = 'list'  # default view is list
if 'page' not in st.session_state:
    st.session_state['page'] = 'main'

# Snowflake connection setup
def create_snowflake_connection():
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA")
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to Snowflake: {e}")
        return None

# Logout function
def logout():
    st.session_state['logged_in'] = False
    st.session_state['access_token'] = None
    st.session_state['page'] = 'main'
    st.rerun()

# Login Page
def login_page():
    st.header("Login / Signup")
    
    option = st.selectbox("Select Login or Signup", ("Login", "Signup"))
    
    if option == "Login":
        st.subheader("Login")
        
        username = st.text_input("Username")
        
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            login(username, password)

    elif option == "Signup":
        
        st.subheader("Signup")
        
        username = st.text_input("Username")
        
        email = st.text_input("Email")
        
        password = st.text_input("Password", type="password")
        
        if st.button("Signup"):
            signup(username, email, password)

# Signup function
def signup(username, email, password):
    response = requests.post(REGISTER_URL, json={
        "username": username,
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        st.success("Account created successfully! Please login.")
    else:
        st.error(f"Signup failed: {response.json().get('detail', 'Unknown error occurred')}")

# Login function 
def login(username, password):
    
   response = requests.post(LOGIN_URL, json={
      "username": username,
      "password": password 
   })
   
   if response.status_code == 200:
       token_data = response.json()
       st.session_state['access_token'] = token_data['access_token']
       st.session_state['logged_in'] = True 
       st.success("Logged in successfully!")
       st.rerun()
   else:
       st.error("Invalid username or password. Please try again.")

# Main Interface depending on login state 
if st.session_state['logged_in']:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Research"])

    if page == "Home":
        if st.session_state['page'] == 'details':
            show_pdf_details()
        else:
            main_app()
    elif page == "Research":
        research_interface()
else:
    login_page()