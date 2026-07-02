import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.core.config import settings

print("os.getenv('CHAT_MODEL'):", os.getenv("CHAT_MODEL"))
print("settings.CHAT_MODEL:", settings.CHAT_MODEL)
