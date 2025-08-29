import random
import os
import itertools

from google import genai
from dotenv import load_dotenv

load_dotenv() # 讀取 .env 檔案
_gemeni_api_keys = (os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 12))
_gemeni_api_keys = tuple(key for key in _gemeni_api_keys if key is not None)

_client_iter = itertools.cycle(_gemeni_api_keys)
for _ in range(random.randint(0, len(_gemeni_api_keys)-1)):
	next(_client_iter)
def get_client():
	return genai.Client(api_key=next(_client_iter))

model = "gemini-2.5-flash"
wait_seconds = 60

if __name__ == "__main__":
	for _ in range(10):
		print(next(_client_iter))