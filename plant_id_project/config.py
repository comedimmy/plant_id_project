import os
from dotenv import load_dotenv
load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
