import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
ACCESS_CODE: str = os.environ["ACCESS_CODE"]
PRODUCTION: bool = os.environ["PRODUCTION"].lower() == "true"
