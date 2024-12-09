import boto3
import requests
import json
import time
import os
from botocore.exceptions import ClientError, NoCredentialsError
from sentence_transformers import SentenceTransformer
import os
from pinecone import Pinecone, ServerlessSpec

# Retrieve API key from environment variable or use a default value
api_key = "xxxxxxxx"

# Initialize the Pinecone client
pinecone_client = Pinecone(api_key=api_key)

index_name = "pdf-text-embeddings"
dimensions = 384  # Ensure this matches your embedding size

# List existing indexes
existing_indexes = pinecone_client.list_indexes().names()
if index_name in existing_indexes:
    # Delete the existing index
    pinecone_client.delete_index(index_name)

# Create a new index
pinecone_client.create_index(
    name=index_name,
    dimension=dimensions,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"  # Replace with your desired region
    )
)

# Connect to the newly created index
index = pinecone_client.Index(index_name)
print(f"Pinecone index '{index_name}' initialized successfully.")


# Load Adobe PDF Services credentials
print("Loading Adobe PDF Services credentials...")
with open("pdfservices-api-credentials.json", "r") as file:
    credentials = json.load(file)

CLIENT_ID = credentials["client_credentials"]["client_id"]
CLIENT_SECRET = credentials["client_credentials"]["client_secret"]
print("Credentials loaded successfully.")

# AWS S3 Configuration
AWS_REGION = "us-east-2"  # AWS region
S3_BUCKET_NAME = "regulationsfia"  # S3 bucket name
buckets_and_prefixes = [
    ("regulationsfia", "financial_regulations/"),
    ("regulationsfia", "sporting_regulations/"),
    ("regulationsfia", "technical_regulations/")
]


# Number of PDFs to process
NUM_PDFS_TO_PROCESS = 1  # Set this to the desired number of PDFs to process

# Local directory to save downloaded files
LOCAL_DIR_PATH = "/Users/shreyabage/Documents/Assignment-5/downloads"

#AWS credentials 
AWS_ACCESS_KEY = "xxxxxxxxx" # AWS Access Key from .env
AWS_SECRET_KEY = "yyyyyyyyy"  # AWS Secret Key from .env

# Initialize S3 Client with specified credentials
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# Function to list PDFs in the specified S3 folder
def list_pdfs_in_s3_folder(bucket_name, folder_prefix):
    try:
        print(f"Listing PDFs in bucket '{bucket_name}' with prefix '{folder_prefix}'...")
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)
        if 'Contents' in response:
            pdf_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.pdf')]
            print(f"Found {len(pdf_files)} PDF(s) in the folder.")
            return pdf_files
        else:
            print("No PDFs found in the specified folder.")
            return []
    except ClientError as e:
        print(f"Error listing objects in S3: {e}")
        return []

# Function to download PDF from S3
def download_pdf_from_s3(bucket_name, object_key, local_dir_path):
    try:
        # Ensure the local directory exists
        if not os.path.exists(local_dir_path):
            os.makedirs(local_dir_path)
            print(f"Created directory {local_dir_path}.")

        local_file_path = os.path.join(local_dir_path, os.path.basename(object_key))
        print(f"Downloading {object_key} from bucket {bucket_name} to {local_file_path}...")
        s3_client.download_file(bucket_name, object_key, local_file_path)
        print(f"File downloaded successfully to {local_file_path}.")
        return local_file_path

    except FileNotFoundError:
        print(f"Error: The directory {local_dir_path} does not exist and could not be created.")
    except NoCredentialsError:
        print("Error: AWS credentials not available.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"Error: The object {object_key} does not exist in the bucket {bucket_name}.")
        elif error_code == '403':
            print("Error: Access denied. Check your permissions.")
        else:
            print(f"Unexpected error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

# Function to get Access Token
def get_access_token(client_id, client_secret):
    print("Requesting access token...")
    url = "https://pdf-services.adobe.io/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"client_id": client_id, "client_secret": client_secret}
    response = requests.post(url, headers=headers, data=data)
    print(f"Access Token Response: {response.status_code}, {response.text}")
    if response.status_code == 200:
        print("Access token retrieved successfully.")
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

# Function to upload PDF File
def upload_pdf(access_token, client_id, file_path):
    print(f"Checking if file exists at: {file_path}...")
    if not os.path.exists(file_path):
        raise Exception(f"File not found at path: {file_path}")

    print("Requesting upload URI...")
    url = "https://pdf-services.adobe.io/assets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": client_id,
        "Content-Type": "application/json",
    }
    data = {"mediaType": "application/pdf"}
    response = requests.post(url, headers=headers, json=data)
    print(f"Upload URI Response: {response.status_code}, {response.text}")
    if response.status_code == 200:
        upload_uri = response.json()["uploadUri"]
        asset_id = response.json()["assetID"]
        print(f"Upload URI: {upload_uri}, Asset ID: {asset_id}")

        print(f"Uploading file to: {upload_uri}")
        with open(file_path, "rb") as file_data:
            headers = {"Content-Type": "application/pdf"}
            upload_response = requests.put(upload_uri, data=file_data, headers=headers)
        print(f"File Upload Response: {upload_response.status_code}, {upload_response.text}")
        if upload_response.status_code == 200:
            print("File uploaded successfully.")
            return asset_id
        else:
            raise Exception(f"Failed to upload PDF: {upload_response.text}")
    else:
        raise Exception(f"Failed to get upload URI: {response.text}")

# Function to create extraction job
def create_extraction_job(access_token, client_id, asset_id):
    print("Creating extraction job...")
    url = "https://pdf-services-ue1.adobe.io/operation/extractpdf"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": client_id,
        "Content-Type": "application/json",
    }
    data = {
        "assetID": asset_id,
        "getCharBounds": False,
        "includeStyling": False,
        "elementsToExtract": ["text"]
    }
    print(f"Extraction Job Payload: {json.dumps(data, indent=2)}")
    response = requests.post(url, headers=headers, json=data)
    print(f"Extraction Job Response: {response.status_code}, {response.text}")
    if response.status_code == 201:
        print("Extraction job created successfully.")
        return response.headers["Location"]
    else:
        print(f"Response Headers: {response.headers}")
        raise Exception(f"Failed to create extraction job: {response.text}")


# Function to poll extraction job
def poll_extraction_job(location_url, access_token, client_id, poll_interval=5):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": client_id,
    }
    while True:
        response = requests.get(location_url, headers=headers)
        if response.status_code == 200:
            job_status = response.json().get("status")
            if job_status == "done":
                print("Extraction job completed successfully.")
                content = response.json().get("content")
                download_url = content.get("downloadUri")
                print(f"Download URL: {download_url}")
                return download_url
            elif job_status == "failed":
                raise Exception("Extraction job failed.")
            else:
                print(f"Job status: {job_status}. Polling again in {poll_interval} seconds...")
                time.sleep(poll_interval)
        else:
            raise Exception(f"Failed to poll job status: {response.status_code}, {response.text}")

output_file_path = "/Users/shreyabage/Documents/Assignment-5/extracted_content.json"
# Function to download extracted content
def download_extracted_content(download_url, output_file_path):
    response = requests.get(download_url)
    if response.status_code == 200:
        with open(output_file_path, "wb") as file:
            file.write(response.content)
        print(f"Extracted content downloaded successfully to {output_file_path}.")
    else:
        raise Exception(f"Failed to download extracted content: {response.text}")
    
# Function to load JSON data
def load_json(output_file_path):
    with open(output_file_path, 'r') as file:
        data = json.load(file)
    return data

# Function to extract text elements from JSON data
def extract_text_elements(data):
    return [element['Text'] for element in data.get('elements', []) if 'Text' in element]

def generate_embeddings(texts, model_name='paraphrase-MiniLM-L6-v2', id_prefix="text_vector", custom_ids=None):
    """
    Generate and flatten embeddings for Pinecone.

    Args:
        texts (list of str): The list of text strings to embed.
        model_name (str): Name of the sentence-transformer model.
        id_prefix (str): Prefix for generated IDs (ignored if custom_ids is provided).
        custom_ids (list of str, optional): Custom IDs to use for each text.

    Returns:
        list of dict: Flattened embeddings ready for Pinecone.
    """
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        raise ValueError("Input 'texts' must be a list of strings.")

    # Load the model and encode texts
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, convert_to_tensor=True)

    # Generate IDs (use custom IDs if provided, else use prefix-based IDs)
    if custom_ids:
        if len(custom_ids) != len(texts):
            raise ValueError("Length of 'custom_ids' must match the number of input texts.")
        ids = custom_ids
    else:
        ids = [f"{id_prefix}_{i}" for i in range(len(texts))]

    # Flatten embeddings
    flattened_embeddings = []
    for text_id, vector in zip(ids, embeddings):
        # Check if vector is a tensor
        if isinstance(vector, list):
            # Already a list, no conversion needed
            vector_list = vector
        else:
            # Convert tensor to a list (move to CPU if necessary)
            vector_list = vector.cpu().numpy().tolist()

        flattened_embeddings.append({"id": text_id, "values": vector_list})

    # Optional debug logging
    print(f"Generated {len(flattened_embeddings)} embeddings for Pinecone.")

    return flattened_embeddings


# Main Workflow
try:
    print("Starting PDF extraction workflow...")

    for bucket_name, folder_prefix in buckets_and_prefixes:
        print(f"\nProcessing bucket: {bucket_name} with prefix: {folder_prefix}")

        # Step 1: List PDFs in the S3 Folder
        pdf_files = list_pdfs_in_s3_folder(bucket_name, folder_prefix)

        if len(pdf_files) == 0:
            print(f"No PDFs found in the specified S3 folder for bucket: {bucket_name}.")
            continue
        if NUM_PDFS_TO_PROCESS > len(pdf_files):
            print(f"Requested number of PDFs to process ({NUM_PDFS_TO_PROCESS}) exceeds available PDFs ({len(pdf_files)}) in bucket: {bucket_name}. Adjusting to process all available PDFs.")
            num_pdfs_to_process = len(pdf_files)
        else:
            num_pdfs_to_process = NUM_PDFS_TO_PROCESS

        # Step 2: Process PDFs
        for i, pdf_file in enumerate(pdf_files[:num_pdfs_to_process]):
            print(f"\nProcessing PDF {i + 1}/{num_pdfs_to_process}: {pdf_file}")

            # Step 3: Download the PDF from S3
            local_file_path = download_pdf_from_s3(bucket_name, pdf_file, LOCAL_DIR_PATH)
            if not local_file_path:
                print(f"Failed to download {pdf_file} from bucket: {bucket_name}. Skipping to next PDF.")
                continue

            # Step 4: Get Access Token
            access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)

            # Step 5: Upload the PDF to Adobe PDF Services
            asset_id = upload_pdf(access_token, CLIENT_ID, local_file_path)

            # Step 6: Create Extraction Job
            location_url = create_extraction_job(access_token, CLIENT_ID, asset_id)

            # Step 7: Poll Extraction Job
            download_url = poll_extraction_job(location_url, access_token, CLIENT_ID)

            # Step 8: Download Extracted Content
            extracted_file_path = os.path.join(LOCAL_DIR_PATH, f"extracted_content_{bucket_name}_{i + 1}.json")
            download_extracted_content(download_url, extracted_file_path)

            # Step 9: Load extracted content
            data = load_json(extracted_file_path)

            # Step 10: Extract text elements
            texts = extract_text_elements(data)

            # Step 11: Generate embeddings
            embeddings = generate_embeddings(texts)
            for embedding in embeddings:
              #print(f"Embedding {i}: Dimension = {len(embedding['values'])}")
            #exit(0)

           # print(f"Generated embeddings for PDF {i + 1}/{num_pdfs_to_process} in bucket {bucket_name}: {embeddings}")

                pdf_embedding_id = f"{bucket_name}_{folder_prefix}_{pdf_file}"  # Unique ID for each PDF
               # print(f"ID: {pdf_embedding_id}")
                index.upsert([(embedding['id'], embedding['values'])])  # Upsert each chunk individually
            print(f"Embeddings for {pdf_embedding_id} upserted into Pinecone successfully.")
            
                # Flatten embeddings into a single list of floats
            ''' if isinstance(embedding, list) and all(isinstance(e, dict) and 'values' in e for e in embedding):
                # Extract all values and flatten into a single list
                    flattened_values = [value for embedding1 in embedding for value in embedding1['values']]
                else:
                    raise ValueError("Invalid embedding format. Must be a list of dictionaries with 'values' as float lists.")

                # Debugging: Print sample of flattened values
                print(f"Flattened Embedding Sample (First 10): {flattened_values[:10]}")
                exit(0)
            '''

           
              


               # Upsert into Pinecone
                #index.upsert([(pdf_embedding_id, flattened_values)])  # Pass flattened list
                

    print("Workflow completed successfully for all PDFs in all buckets.")
except Exception as e:
     print(f"Error: {e}")

    
''' 
(assignment-5-py3.11) shreyabage@Shreyas-Laptop Assignment-5 % python adobe4.py
Pinecone index 'pdf-text-embeddings' initialized successfully.
Loading Adobe PDF Services credentials...
Credentials loaded successfully.
Starting PDF extraction workflow...

Processing bucket: regulationsfia with prefix: financial_regulations/
Listing PDFs in bucket 'regulationsfia' with prefix 'financial_regulations/'...
Found 27 PDF(s) in the folder.

Processing PDF 1/1: financial_regulations/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf
Downloading financial_regulations/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf from bucket regulationsfia to /Users/shreyabage/Documents/Assignment-5/downloads/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf...
File downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf.
Requesting access token...
Access Token Response: 200, {"access_token":"xxxxxxxx","token_type":"bearer","expires_in":86399}
Access token retrieved successfully.
Checking if file exists at: /Users/shreyabage/Documents/Assignment-5/downloads/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf...
Requesting upload URI...
Upload URI Response: 200, {"uploadUri":"https://dcplatformstorageservice-prod-us-east-1.s3-accelerate.amazonaws.com/9dc3385cc6394d538fa673ba8c8d92e2_137D1DAC6747985C0A495E19%40techacct.adobe.com/25e71250-9c88-41ee-affe-5dd418446bbe?X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQDAwgSQ%2BM12JZfIUQ2KTI41Rs%2BoBLNG6VTlJ8HEA7QaYAIgWi6RIPdHD1Wv2P0QnmUT56S%2BVDM0vLN3%2BUd6SdijFukqmAUIahAAGgw0MjA1MzM0NDU5ODIiDHfBUzpWvZSHSEJQrir1BJd5oznImWCa%2BMerdm0rHiBoN8Xv1qs1aKPfwpM2ozT9FNJEutqVEhQf7s4ilxWiQrk%2F7GZRsedoteaanZrIxve7dzyNKQspt6om6AKM0ik2Zo7qsOcV0YB1S4vxRFpOslHfpaY6ZzN6KULOShxG5waHNtnU05QraKwcHKoarxd9CqD3EjOeXtSlXU4ZpwKfVRcfps4tsdTM7gWYRgkCrTQGgXGCYSYb2drQ%2FRen%2F5P9tNfPVJi19al4XJQIn6cfN5%2Fk1j2u3a4mmeLkV9DDLMNSBQueo7KrdYkW8IHEb4I6xP5yE0zlFhuKZm%2BN%2BWNbV6Hp7ISILI8r7xufH32MZg6ez0SG%2BuQLW750e%2FaNeS1ANB1MJclAfMCm4jhUDHW589RE9wHlbYoVoQWUV1rXP90KbOBffpPjYWPaEj3sHYv9oK9lh1WxOC4LjLzN6peJijJzJvQoWKIUZqizA6%2FcJ2zbefbNE7C%2BAmFVsK0ctkSh4QE4A7nK9Uy%2F2NzK6TGiLokJiv7QC5FbzMecJUF2dKK%2BhzqNnb0gY7K%2BvO2fyyT3b0eQMOMd6oJo4jnlmWmyQJX3Wki7a9%2BIEX5P2fJJSvCfKzxBaUw8WsJ9oUZyDAdUmMtZMEzlmbAW%2BsxDX4Aas0mGhF05YMw57XwnceePq4INXyvA%2B06pVPhpjiC86W%2FQEAbKkghlVGhM4MTHH8niAOMWQgLr%2B8P0mDNilQmYOT2FX6lHJDkJooX5w5lWONLD7sXA1xmJrdzXfosOJFsx8HZ734i1x2ZQ8b5sVygD9YhDQ%2BXHLZsqosMZ8u49OroYxxEIzJlcGmXkl16umX6e1GBJKDbTMOSG2boGOpsB%2FNwWeKxIe35AV%2FXyRp6wpjJmYXr%2BOgtMZqMU5vFMsfKkcXrrUDMoWaJE5SB7LnjYkWUk391pM8Ne%2BlA3QFchRlqcGUrExt9KPaP6Fj5bwxJHo%2BBPeDnnRWvre8Jhz%2BfbwzOKLk5nkPvcwwm759dKAlKaQ81ZHctUjQLJDzSQDDeGlGKlur0IZsluEBdgF1%2BPsUNs3tHjLQx8umc%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20241209T020745Z&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Expires=3600&X-Amz-Credential=ASIAWD2N7EVPGYXDDWGB%2F20241209%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=890e18b203f691a8593c6bc5a9061147ee5e4aae3a9ea3ac5a0e59b48390f309","assetID":"urn:aaid:AS:UE1:35de471f-137a-4ea1-af02-fd1a036c1868"}
Upload URI: https://dcplatformstorageservice-prod-us-east-1.s3-accelerate.amazonaws.com/9dc3385cc6394d538fa673ba8c8d92e2_137D1DAC6747985C0A495E19%40techacct.adobe.com/25e71250-9c88-41ee-affe-5dd418446bbe?X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQDAwgSQ%2BM12JZfIUQ2KTI41Rs%2BoBLNG6VTlJ8HEA7QaYAIgWi6RIPdHD1Wv2P0QnmUT56S%2BVDM0vLN3%2BUd6SdijFukqmAUIahAAGgw0MjA1MzM0NDU5ODIiDHfBUzpWvZSHSEJQrir1BJd5oznImWCa%2BMerdm0rHiBoN8Xv1qs1aKPfwpM2ozT9FNJEutqVEhQf7s4ilxWiQrk%2F7GZRsedoteaanZrIxve7dzyNKQspt6om6AKM0ik2Zo7qsOcV0YB1S4vxRFpOslHfpaY6ZzN6KULOShxG5waHNtnU05QraKwcHKoarxd9CqD3EjOeXtSlXU4ZpwKfVRcfps4tsdTM7gWYRgkCrTQGgXGCYSYb2drQ%2FRen%2F5P9tNfPVJi19al4XJQIn6cfN5%2Fk1j2u3a4mmeLkV9DDLMNSBQueo7KrdYkW8IHEb4I6xP5yE0zlFhuKZm%2BN%2BWNbV6Hp7ISILI8r7xufH32MZg6ez0SG%2BuQLW750e%2FaNeS1ANB1MJclAfMCm4jhUDHW589RE9wHlbYoVoQWUV1rXP90KbOBffpPjYWPaEj3sHYv9oK9lh1WxOC4LjLzN6peJijJzJvQoWKIUZqizA6%2FcJ2zbefbNE7C%2BAmFVsK0ctkSh4QE4A7nK9Uy%2F2NzK6TGiLokJiv7QC5FbzMecJUF2dKK%2BhzqNnb0gY7K%2BvO2fyyT3b0eQMOMd6oJo4jnlmWmyQJX3Wki7a9%2BIEX5P2fJJSvCfKzxBaUw8WsJ9oUZyDAdUmMtZMEzlmbAW%2BsxDX4Aas0mGhF05YMw57XwnceePq4INXyvA%2B06pVPhpjiC86W%2FQEAbKkghlVGhM4MTHH8niAOMWQgLr%2B8P0mDNilQmYOT2FX6lHJDkJooX5w5lWONLD7sXA1xmJrdzXfosOJFsx8HZ734i1x2ZQ8b5sVygD9YhDQ%2BXHLZsqosMZ8u49OroYxxEIzJlcGmXkl16umX6e1GBJKDbTMOSG2boGOpsB%2FNwWeKxIe35AV%2FXyRp6wpjJmYXr%2BOgtMZqMU5vFMsfKkcXrrUDMoWaJE5SB7LnjYkWUk391pM8Ne%2BlA3QFchRlqcGUrExt9KPaP6Fj5bwxJHo%2BBPeDnnRWvre8Jhz%2BfbwzOKLk5nkPvcwwm759dKAlKaQ81ZHctUjQLJDzSQDDeGlGKlur0IZsluEBdgF1%2BPsUNs3tHjLQx8umc%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20241209T020745Z&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Expires=3600&X-Amz-Credential=ASIAWD2N7EVPGYXDDWGB%2F20241209%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=890e18b203f691a8593c6bc5a9061147ee5e4aae3a9ea3ac5a0e59b48390f309, Asset ID: urn:aaid:AS:UE1:35de471f-137a-4ea1-af02-fd1a036c1868
Uploading file to: https://dcplatformstorageservice-prod-us-east-1.s3-accelerate.amazonaws.com/9dc3385cc6394d538fa673ba8c8d92e2_137D1DAC6747985C0A495E19%40techacct.adobe.com/25e71250-9c88-41ee-affe-5dd418446bbe?X-Amz-Security-Token=IQoJb3JpZ2luX2VjELL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQDAwgSQ%2BM12JZfIUQ2KTI41Rs%2BoBLNG6VTlJ8HEA7QaYAIgWi6RIPdHD1Wv2P0QnmUT56S%2BVDM0vLN3%2BUd6SdijFukqmAUIahAAGgw0MjA1MzM0NDU5ODIiDHfBUzpWvZSHSEJQrir1BJd5oznImWCa%2BMerdm0rHiBoN8Xv1qs1aKPfwpM2ozT9FNJEutqVEhQf7s4ilxWiQrk%2F7GZRsedoteaanZrIxve7dzyNKQspt6om6AKM0ik2Zo7qsOcV0YB1S4vxRFpOslHfpaY6ZzN6KULOShxG5waHNtnU05QraKwcHKoarxd9CqD3EjOeXtSlXU4ZpwKfVRcfps4tsdTM7gWYRgkCrTQGgXGCYSYb2drQ%2FRen%2F5P9tNfPVJi19al4XJQIn6cfN5%2Fk1j2u3a4mmeLkV9DDLMNSBQueo7KrdYkW8IHEb4I6xP5yE0zlFhuKZm%2BN%2BWNbV6Hp7ISILI8r7xufH32MZg6ez0SG%2BuQLW750e%2FaNeS1ANB1MJclAfMCm4jhUDHW589RE9wHlbYoVoQWUV1rXP90KbOBffpPjYWPaEj3sHYv9oK9lh1WxOC4LjLzN6peJijJzJvQoWKIUZqizA6%2FcJ2zbefbNE7C%2BAmFVsK0ctkSh4QE4A7nK9Uy%2F2NzK6TGiLokJiv7QC5FbzMecJUF2dKK%2BhzqNnb0gY7K%2BvO2fyyT3b0eQMOMd6oJo4jnlmWmyQJX3Wki7a9%2BIEX5P2fJJSvCfKzxBaUw8WsJ9oUZyDAdUmMtZMEzlmbAW%2BsxDX4Aas0mGhF05YMw57XwnceePq4INXyvA%2B06pVPhpjiC86W%2FQEAbKkghlVGhM4MTHH8niAOMWQgLr%2B8P0mDNilQmYOT2FX6lHJDkJooX5w5lWONLD7sXA1xmJrdzXfosOJFsx8HZ734i1x2ZQ8b5sVygD9YhDQ%2BXHLZsqosMZ8u49OroYxxEIzJlcGmXkl16umX6e1GBJKDbTMOSG2boGOpsB%2FNwWeKxIe35AV%2FXyRp6wpjJmYXr%2BOgtMZqMU5vFMsfKkcXrrUDMoWaJE5SB7LnjYkWUk391pM8Ne%2BlA3QFchRlqcGUrExt9KPaP6Fj5bwxJHo%2BBPeDnnRWvre8Jhz%2BfbwzOKLk5nkPvcwwm759dKAlKaQ81ZHctUjQLJDzSQDDeGlGKlur0IZsluEBdgF1%2BPsUNs3tHjLQx8umc%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20241209T020745Z&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Expires=3600&X-Amz-Credential=ASIAWD2N7EVPGYXDDWGB%2F20241209%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=890e18b203f691a8593c6bc5a9061147ee5e4aae3a9ea3ac5a0e59b48390f309
File Upload Response: 200, 
File uploaded successfully.
Creating extraction job...
Extraction Job Payload: {
  "assetID": "urn:aaid:AS:UE1:35de471f-137a-4ea1-af02-fd1a036c1868",
  "getCharBounds": false,
  "includeStyling": false,
  "elementsToExtract": [
    "text"
  ]
}
Extraction Job Response: 201, 
Extraction job created successfully.
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Extraction job completed successfully.
Extracted content downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/extracted_content_regulationsfia_1.json.
Generated 1277 embeddings for Pinecone.
Embeddings for regulationsfia_financial_regulations/_financial_regulations/2021_formula_1_financial_regulations_-_iss_3_-_2020-05-27_0.pdf upserted into Pinecone successfully.

Processing bucket: regulationsfia with prefix: sporting_regulations/
Listing PDFs in bucket 'regulationsfia' with prefix 'sporting_regulations/'...
Found 70 PDF(s) in the folder.

Processing PDF 1/1: sporting_regulations/1-2018_sporting_regulations_2017-12-19.pdf
Downloading sporting_regulations/1-2018_sporting_regulations_2017-12-19.pdf from bucket regulationsfia to /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_sporting_regulations_2017-12-19.pdf...
File downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_sporting_regulations_2017-12-19.pdf.
Requesting access token...
Access Token Response: 200, {"access_token":"eyJhbGciOiJSUzI1NiIsIng1dSI6Imltc19uYTEta2V5LWF0LTEuY2VyIiwia2lkIjoiaW1zX25hMS1rZXktYXQtMSIsIml0dCI6ImF0In0.eyJpZCI6IjE3MzM3MTAyMTczMTFfZGRiNjhlYmItZmQ1Ny00M2YxLTg2NDctYWJhOTkyOTRlOGM2X3VlMSIsIm9yZyI6IjEyOEYxREFDNjc0NzhGNEMwQTQ5NUNGQUBBZG9iZU9yZyIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiI5ZGMzMzg1Y2M2Mzk0ZDUzOGZhNjczYmE4YzhkOTJlMiIsInVzZXJfaWQiOiIxMzdEMURBQzY3NDc5ODVDMEE0OTVFMTlAdGVjaGFjY3QuYWRvYmUuY29tIiwiYXMiOiJpbXMtbmExIiwiYWFfaWQiOiIxMzdEMURBQzY3NDc5ODVDMEE0OTVFMTlAdGVjaGFjY3QuYWRvYmUuY29tIiwiY3RwIjozLCJtb2kiOiJhOGY1NDI0YyIsImV4cGlyZXNfaW4iOiI4NjQwMDAwMCIsImNyZWF0ZWRfYXQiOiIxNzMzNzEwMjE3MzExIiwic2NvcGUiOiJEQ0FQSSxvcGVuaWQsQWRvYmVJRCJ9.gePFHtOQxkFqyBrKyFfZaVkR444e-ydEQ1ZzAzDXYYVf97R3CMvTL-hdiDlWEX6wLmLHA_jPlqKTdgrJO_JbWVPkt0v-f4LJNxj_fbgMClluWYpxM_oJ-oZOSm5vyPxa3aMxL05nj5FN7gS6usJ18ISDP03hoC2kbfOHgp0bQN_vL-2d3Cw67NEglD6dDBMeQT0abjMkVaXCW7Y5wQg9Ic1QXakB84M9xuNz0DyWYPbzFjAvUhLpe3Yrx-op1yxemuZzljhiin8hpB0fCMXZAnPdR-gJIXMxSi22pPQDZqS7kfe1V-z0Df0d3m1EOBq8g1UlivEyyNCiG2YDxRCj_g","token_type":"bearer","expires_in":86399}
Access token retrieved successfully.
Checking if file exists at: /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_sporting_regulations_2017-12-19.pdf...
Requesting upload URI...
File Upload Response: 200, 
File uploaded successfully.
Creating extraction job...
Extraction Job Payload: {
  "assetID": "urn:aaid:AS:UE1:19ff5353-c18e-4e90-8b8f-60c3f52bf47a",
  "getCharBounds": false,
  "includeStyling": false,
  "elementsToExtract": [
    "text"
  ]
}
Extraction Job Response: 201, 
Extraction job created successfully.
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Extraction job completed successfully.
Extracted content downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/extracted_content_regulationsfia_1.json.
Generated 2248 embeddings for Pinecone.
Embeddings for regulationsfia_sporting_regulations/_sporting_regulations/1-2018_sporting_regulations_2017-12-19.pdf upserted into Pinecone successfully.

Processing bucket: regulationsfia with prefix: technical_regulations/
Listing PDFs in bucket 'regulationsfia' with prefix 'technical_regulations/'...
Found 58 PDF(s) in the folder.

Processing PDF 1/1: technical_regulations/1-2018_technical_regulations_2017-12-19_0.pdf
Downloading technical_regulations/1-2018_technical_regulations_2017-12-19_0.pdf from bucket regulationsfia to /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_technical_regulations_2017-12-19_0.pdf...
File downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_technical_regulations_2017-12-19_0.pdf.
Requesting access token...
Access Token Response: 200, {"access_token":"eyJhbGciOiJSUzI1NiIsIng1dSI6Imltc19uYTEta2V5LWF0LTEuY2VyIiwia2lkIjoiaW1zX25hMS1rZXktYXQtMSIsIml0dCI6ImF0In0.eyJpZCI6IjE3MzM3MTA0ODU0MTBfYzQ0ZTdlYjEtYTBkMy00Njg4LTg0OGUtMmE1OWI1ZGMzYjU4X3VlMSIsIm9yZyI6IjEyOEYxREFDNjc0NzhGNEMwQTQ5NUNGQUBBZG9iZU9yZyIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiI5ZGMzMzg1Y2M2Mzk0ZDUzOGZhNjczYmE4YzhkOTJlMiIsInVzZXJfaWQiOiIxMzdEMURBQzY3NDc5ODVDMEE0OTVFMTlAdGVjaGFjY3QuYWRvYmUuY29tIiwiYXMiOiJpbXMtbmExIiwiYWFfaWQiOiIxMzdEMURBQzY3NDc5ODVDMEE0OTVFMTlAdGVjaGFjY3QuYWRvYmUuY29tIiwiY3RwIjozLCJtb2kiOiI4NWVkMmQyNSIsImV4cGlyZXNfaW4iOiI4NjQwMDAwMCIsInNjb3BlIjoiRENBUEksb3BlbmlkLEFkb2JlSUQiLCJjcmVhdGVkX2F0IjoiMTczMzcxMDQ4NTQxMCJ9.Is_FZoCXA3-nsVlaU-X6GegXOIFvopMZYAZ2SavmVFdTXqh-OVbS_avlzgdnRrNT7xIHCbHRJFvlS2qPMU3AyH2MDZjEa7gTBa1AowfKd_yK0i79fhXZP5ee8OHIFu73QFSmUTjIyip7NYxILoURWDxJ-51nal6YENB9xK2hj134BDa5tHqTTHH2C3lK8DJIlfiMTA4W-kXKBGitY4TrS-zdb3fnGv-rvmDKgp9Pz0f49yj7BMEWBj1tRHw_niCk3sj_E-vGWoJdLvviXb7Lt9KEBSKUaL88w6M6ZEZxyS5fIrKPAHmSJYkQTQk4PrlMSENkdiOA3Fotp8YdkaJQhQ","token_type":"bearer","expires_in":86399}
Access token retrieved successfully.
Checking if file exists at: /Users/shreyabage/Documents/Assignment-5/downloads/1-2018_technical_regulations_2017-12-19_0.pdf...
Requesting upload URI...
File Upload Response: 200, 
File uploaded successfully.
Creating extraction job...
Extraction Job Payload: {
  "assetID": "urn:aaid:AS:UE1:ac6194b4-1470-4beb-b949-220094337210",
  "getCharBounds": false,
  "includeStyling": false,
  "elementsToExtract": [
    "text"
  ]
}
Extraction Job Response: 201, 
Extraction job created successfully.
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Job status: in progress. Polling again in 5 seconds...
Extraction job completed successfully.
Extracted content downloaded successfully to /Users/shreyabage/Documents/Assignment-5/downloads/extracted_content_regulationsfia_1.json.
Generated 3056 embeddings for Pinecone.
Embeddings for regulationsfia_technical_regulations/_technical_regulations/1-2018_technical_regulations_2017-12-19_0.pdf upserted into Pinecone successfully.
Workflow completed successfully for all PDFs in all buckets.
(assignment-5-py3.11) shreyabage@Shreyas-Laptop Assignment-5 % 
'''