# config.py

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings  # Pydantic v2 kompatibel!

load_dotenv()

class Settings(BaseSettings):
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY")
    S3_REGION: str = os.getenv("S3_REGION")

settings = Settings()

if __name__ == "__main__":
    # Mini-Test: Zeigt dir, ob alles geladen wird
    print(f"S3 Bucket: {settings.S3_BUCKET_NAME}")
    print(f"Region: {settings.S3_REGION}")
