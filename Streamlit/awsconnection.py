import boto3
import os
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))

# Build the path to the .env file
env_path = os.path.join(script_dir, '.env')

# Load the .env file
load_dotenv(dotenv_path=env_path)

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name='us-east-2'
)

# List objects in the bucket
response = s3.list_objects_v2(Bucket="f1wiki", Prefix="history/")
if 'Contents' in response:
    for obj in response['Contents']:
        print(obj['Key'])
else:
    print("No objects found.")