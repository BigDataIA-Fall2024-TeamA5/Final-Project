import boto3
import os
from dotenv import load_dotenv

s3_client = boto3.client('s3')
load_dotenv(dotenv_path='/Users/aniketpatole/Documents/GitHub/New/Projects/BigData/Final-Project/.env')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
# Replace with your bucket name

try:
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME)
    print("Bucket is accessible. Contents:")
    for obj in response.get('Contents', []):
        print(obj['Key'])
except Exception as e:
    print(f"Error accessing bucket: {e}")

