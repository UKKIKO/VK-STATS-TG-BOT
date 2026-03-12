import os
from dotenv import load_dotenv

load_dotenv()

VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
TG_ACCESS_TOKEN = os.getenv("TG_ACCESS_TOKEN")