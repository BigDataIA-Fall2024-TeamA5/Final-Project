import requests
import json
import time

# Load credentials
print("Loading credentials...")
with open("pdfservices-api-credentials.json", "r") as file:
    credentials = json.load(file)

CLIENT_ID = credentials["client_credentials"]["client_id"]
CLIENT_SECRET = credentials["client_credentials"]["client_secret"]
print("Credentials loaded successfully.")

# Get Access Token
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

#Validate Payload Elements
def validate_payload_elements(access_token, client_id):
    print("Validating payload elements...")
    test_payload = {"elements": ["text"]}
    url = "https://pdf-services.adobe.io/some-validation-endpoint"  # Replace with the correct API validation endpoint if available
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": client_id,
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=test_payload)
    if response.status_code == 200:
        print("Payload elements are valid.")
    else:
        print(f"Payload validation failed: {response.status_code}, {response.text}")
        raise Exception("Invalid payload elements.")

# Upload PDF File
def upload_pdf(access_token, client_id, file_path):
    print(f"Checking if file exists at: {file_path}...")
    try:
        with open(file_path, "rb") as file_data:
            print("File located successfully.")
    except FileNotFoundError:
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

#Verify Asset Details
def verify_asset_details(access_token, client_id, asset_id):
    print(f"Verifying asset details for Asset ID: {asset_id}...")
    url = f"https://pdf-services.adobe.io/assets/{asset_id}"  # Replace with correct endpoint for asset details if available
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": client_id,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Asset details: {response.json()}")
        return response.json()
    else:
        print(f"Asset verification failed: {response.status_code}, {response.text}")
        raise Exception("Invalid asset details.")

# Create Extraction Job
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
        "elementsToExtract": [
            "text"
        ]
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
    
    #poll extraction function 

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
                print(f"RESULTS: {response.json().get('result')}")
                print(f"RESPONSE: {response.json()} ")
                content = response.json().get("content")
                print(f"CONTENT: {content}")
                download_url = content.get("downloadUri")
                print(f"Download URL: {download_url}")
                return(download_url)
            elif job_status == "failed":
                raise Exception("Extraction job failed.")
            else:
                print(f"Job status: {job_status}. Polling again in {poll_interval} seconds...")
                time.sleep(poll_interval)
        else:
            raise Exception(f"Failed to poll job status: {response.status_code}, {response.text}")
        
def download_extracted_content(download_url, output_file_path):
    response = requests.get(download_url)
    if response.status_code == 200:
        with open(output_file_path, "wb") as file:
            file.write(response.content)
        print(f"Extracted content downloaded successfully to {output_file_path}.")
    else:
        raise Exception(f"Failed to download extracted content: {response.text}")



# Main Workflow
try:
    print("Starting PDF extraction workflow...")
    file_path = "/Users/shreyabage/Documents/Assignment-5/Review.pdf"
    output_file_path = "/Users/shreyabage/Documents/Assignment-5/extracted_file.json"
    # Step 1: Get Access Token
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)

    # Step 2: Validate Payload Elements
    #validate_payload_elements(access_token, CLIENT_ID)

    # Step 3: Upload the PDF
    asset_id = upload_pdf(access_token, CLIENT_ID, file_path)

    # Step 4: Verify Asset Details
    verify_asset_details(access_token, CLIENT_ID, asset_id)

    # Step 5: Create Extraction Job
    location_url = create_extraction_job(access_token, CLIENT_ID, asset_id)

    #step 6: poll extraction job 
    download_url = poll_extraction_job(location_url, access_token, CLIENT_ID, poll_interval=5)

    #step 7: download extracted file
    download_extracted_content(download_url, output_file_path)


    print("Workflow completed successfully.")
except Exception as e:
    print(f"Error: {e}")

