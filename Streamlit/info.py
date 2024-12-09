import streamlit as st
import boto3
import pandas as pd
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Function to add custom CSS styles for a balanced background and readable content
def add_custom_styles():
    st.markdown("""
        <style>
        /* Add the background image with reduced opacity and fixed positioning */
        [data-testid="stAppViewContainer"] {
            background-image: url('Images/Paddockpal.png');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            filter: brightness(50%) contrast(70%);
            z-index: -1;
        }
        
        /* Apply a solid background to the content area to ensure readability */
        .main-content {
            max-width: 1200px;
            margin: auto;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1);
            position: relative;
            z-index: 1; /* Ensure the content is always above the background */
        }
        
        .history-section {
            margin-bottom: 40px;
            border-bottom: 2px solid #a2a9b1;
            padding-bottom: 30px;
        }

        .selection-section {
            margin-top: 40px;
            padding-top: 20px;
        }

        .image-caption {
            font-size: 0.9em;
            color: #666;
            text-align: center;
        }

        .section-title {
            border-bottom: 1px solid #a2a9b1;
            padding-bottom: 0.3em;
            margin-top: 1em;
        }
        </style>
    """, unsafe_allow_html=True)

# Initialize S3 client
@st.cache_resource
def init_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

# Load History content from S3
@st.cache_data
def load_history_content(bucket):
    s3 = init_s3_client()
    try:
        # Get history text content
        history_text = s3.get_object(Bucket=bucket, Key='History/f1_history.txt')
        history_content = history_text['Body'].read().decode('utf-8')
        
        # Get history images
        images = []
        image_response = s3.list_objects_v2(Bucket=bucket, Prefix='History/images/')
        if 'Contents' in image_response:
            for obj in image_response['Contents']:
                if obj['Key'].endswith(('.jpg', '.png', '.jpeg')):
                    img_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                    images.append({
                        'key': obj['Key'],
                        'data': BytesIO(img_obj['Body'].read())
                    })
        return {'content': history_content, 'images': images}
    except Exception as e:
        st.error(f"Error loading history data: {str(e)}")
        return None

# Load Drivers and Tracks content from S3
@st.cache_data
def load_section_data(bucket, section):
    s3 = init_s3_client()
    try:
        data = {}
        # Get text content
        response = s3.list_objects_v2(Bucket=bucket, Prefix=f'{section}/')
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('.txt'):
                    text_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                    data['content'] = text_obj['Body'].read().decode('utf-8')
                    
        # Get images
        image_response = s3.list_objects_v2(Bucket=bucket, Prefix=f'{section}/images/')
        if 'Contents' in image_response:
            data['images'] = []
            for obj in image_response['Contents']:
                if obj['Key'].endswith(('.jpg', '.png', '.jpeg')):
                    img_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                    data['images'].append({
                        'key': obj['Key'],
                        'data': BytesIO(img_obj['Body'].read())
                    })
        return data
    except Exception as e:
        st.error(f"Error loading {section} data: {str(e)}")
        return None

# Show Information on the page
def show_info():
    add_custom_styles()
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.title("Formula 1 Encyclopedia")
    
    # History Section
    st.markdown('<div class="history-section">', unsafe_allow_html=True)
    st.header("F1 History")
    history_data = load_history_content("f1wikipedia")
    if history_data:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(history_data['content'])
        with col2:
            for image in history_data.get('images', []):
                st.image(image['data'], caption=image['key'].split('/')[-1])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Selection Section
    st.markdown('<div class="selection-section">', unsafe_allow_html=True)
    st.header("Explore More")
    
    # Tabs for Drivers and Tracks
    driver_tab, track_tab = st.tabs(["Drivers", "Tracks"])
    
    with driver_tab:
        drivers_data = load_section_data("f1wikipedia", "Drivers")
        if drivers_data and 'content' in drivers_data:
            driver_names = drivers_data['content'].split('\n')  # Assuming each line is a driver name
            selected_driver = st.selectbox("Select a Driver", driver_names)
            
            if selected_driver:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(selected_driver)
                    # Display driver-specific content
                with col2:
                    # Display driver-specific images
                    for image in drivers_data.get('images', []):
                        if selected_driver.lower() in image['key'].lower():
                            st.image(image['data'])
    
    with track_tab:
        tracks_data = load_section_data("f1wikipedia", "Tracks")
        if tracks_data and 'content' in tracks_data:
            track_names = tracks_data['content'].split('\n')  # Assuming each line is a track name
            selected_track = st.selectbox("Select a Track", track_names)
            
            if selected_track:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(selected_track)
                    # Display track-specific content
                with col2:
                    # Display track-specific images
                    for image in tracks_data.get('images', []):
                        if selected_track.lower() in image['key'].lower():
                            st.image(image['data'])
    st.markdown('</div>', unsafe_allow_html=True)

# Run the page content
if __name__ == "__main__":
    show_info()
