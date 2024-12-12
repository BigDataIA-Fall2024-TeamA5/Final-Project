import streamlit as st
import boto3
import os
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables
load_dotenv()

# Initialize S3 client
@st.cache_resource
def init_s3_client():
    """Initialize and cache the S3 client."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

@st.cache_data
def load_history_content(bucket):
    """Load history content and images from S3."""
    s3 = init_s3_client()
    try:
        history_text = s3.get_object(Bucket=bucket, Key='History/f1_history.txt')
        history_content = history_text['Body'].read().decode('utf-8')

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

def add_custom_styles():
    """Add custom CSS styles to remove the background image."""
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background: none; /* Clear the background image */
        }
        </style>
    """, unsafe_allow_html=True)

def show_info():
    """Display the Formula 1 Encyclopedia page."""
    add_custom_styles()  # Apply the custom styles to remove the background

    st.title("Formula 1 Encyclopedia")

    # History Section
    st.header("F1 History")
    history_data = load_history_content("f1wikipedia")

    if history_data:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(history_data['content'])
        with col2:
            for image in history_data['images']:
                st.image(image['data'], caption=image['key'].split('/')[-1])
    else:
        st.warning("History data could not be loaded. Please check your S3 configuration or network connection.")

if __name__ == "__main__":
    show_info()
