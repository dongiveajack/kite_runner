import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_AUTH_TOKEN = os.getenv("KITE_AUTH_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "kite_history")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")
