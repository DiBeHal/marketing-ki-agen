# storage.py

import boto3
from botocore.exceptions import NoCredentialsError
from config import settings

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT
    )

def upload_file(local_file_path: str, s3_key: str):
    s3 = get_s3_client()
    try:
        print(f"📂 Bucket: {settings.S3_BUCKET_NAME}")
        s3.upload_file(
            local_file_path,
            settings.S3_BUCKET_NAME,
            s3_key
        )
        print(f"✅ Uploaded {local_file_path} to s3://{settings.S3_BUCKET_NAME}/{s3_key}")
    except FileNotFoundError:
        print("❌ File not found!")
    except NoCredentialsError:
        print("❌ Credentials not available!")

def list_files():
    s3 = get_s3_client()
    response = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME)
    if 'Contents' in response:
        print(f"📂 Objects in {settings.S3_BUCKET_NAME}:")
        for obj in response['Contents']:
            print(f" - {obj['Key']}")
    else:
        print(f"📂 Bucket {settings.S3_BUCKET_NAME} is empty.")

def check_bucket():
    s3 = get_s3_client()
    response = s3.list_buckets()
    print("📂 Deine Buckets:")
    for bucket in response['Buckets']:
        print(f" - {bucket['Name']}")
