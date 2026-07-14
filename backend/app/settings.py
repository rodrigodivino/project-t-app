import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
ACCESS_CODE = os.environ.get("ACCESS_CODE", "dev")
