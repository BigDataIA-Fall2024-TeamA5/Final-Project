import os
import time
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# Set up directories
project_directory = "/Users/shreyabage/Documents/Assignment-5"
download_directory = os.path.join(project_directory, "FinalProject_data")
os.makedirs(download_directory, exist_ok=True)

# Configure AWS S3
AWS_ACCESS_KEY = ""  # AWS Access Key from .env
AWS_SECRET_KEY = ""  # AWS Secret Key from .env
AWS_REGION = "us-east-2"  # AWS region
s3_bucket_name = "regulationsfia"  # S3 bucket name

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_experimental_option('prefs', {
    "download.default_directory": download_directory,  # Save downloads temporarily
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True  # Open PDFs directly in the browser
})
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--log-level=3")

# Initialize WebDriver
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

try:
    # Open the webpage and download the PDF
    URL = "https://www.fia.com/regulation/category/110"
    driver.get(URL)
    driver.implicitly_wait(5)

    try:
        # Attempt to find and click the "Reject All" button for cookies
        reject_button = driver.find_element(By.XPATH, '//button[contains(text(), "Reject All")]')
        reject_button.click()
        print("Successfully clicked the 'Reject All' button!")
    except NoSuchElementException:
        # If the button isn't found, proceed without clicking it
        print("Could not find the 'Reject All' button. Proceeding without clicking it.")

    # Find all <a> tags on the page
    all_a_tags = driver.find_elements(By.XPATH, "//a")
    for a in all_a_tags:
        href = a.get_attribute('href')
        if href and '.pdf' in href:
            print(f"Found PDF link: {href}")

            # Extract the exact file name from the href
            file_name = href.split("/")[-1]  # Extract filename from the href

            # Determine the S3 subfolder based on the href
            if "sporting" in href.lower():
                s3_folder_path = "sporting_regulations/"
            elif "technical" in href.lower():
                s3_folder_path = "technical_regulations/"
            elif "financial" in href.lower():
                s3_folder_path = "financial_regulations/"
            else:
                s3_folder_path = "uncategorized/"  # Optional fallback

            # Debugging statements before clicking
            print(f"Categorized PDF as: {s3_folder_path}")
            print("Attempting to click on the PDF link...")

            # Execute the click action
            driver.execute_script("arguments[0].click();", a)

            # Debugging statement after click
            print("Click executed successfully.")

            # Wait for the file to appear in the download directory
            print("Waiting for the PDF to be downloaded...")
            for _ in range(20):  # Wait up to 20 seconds
                downloaded_files = os.listdir(download_directory)
                pdf_files = [file for file in downloaded_files if file.endswith(".pdf")]
                if pdf_files:
                    downloaded_file_path = os.path.join(download_directory, pdf_files[0])
                    renamed_file_path = os.path.join(download_directory, file_name)

                    # Rename the downloaded file to match the href filename
                    os.rename(downloaded_file_path, renamed_file_path)
                    print(f"File renamed to match href: {renamed_file_path}")

                    # Upload to S3 using the href filename
                    print("Uploading the PDF to S3...")
                    s3_key = os.path.join(s3_folder_path, file_name)
                    s3_client.upload_file(renamed_file_path, s3_bucket_name, s3_key)
                    print(f"File uploaded to S3 successfully: s3://{s3_bucket_name}/{s3_key}")

                    # Remove the local copy after uploading to S3
                    os.remove(renamed_file_path)
                    print("Local copy of the file deleted after upload.")

                    # Continue to the next link to process all PDFs
                    break
                time.sleep(1)
            else:
                print("PDF download did not complete within the expected time.")

except Exception as e:
    # Handle any exceptions that may occur
    print(f"An error occurred: {e}")

finally:
    # Always quit the driver to avoid resource leaks
    driver.quit()

# S3 Bucket Path
print(f"PDF files are stored in the S3 bucket: s3://{s3_bucket_name}")
