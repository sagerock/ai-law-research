#!/usr/bin/env python3
"""
Test GPT-5 API to see actual response structure
"""
import os
import requests
import json

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY environment variable not set")
    exit(1)

# Test GPT-5 Responses API
print("Testing GPT-5 Responses API...")
print("="*80)

response = requests.post(
    "https://api.openai.com/v1/responses",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "gpt-5-mini",
        "input": "Write a one sentence summary of the legal concept of 'stare decisis'.",
        "reasoning": {
            "effort": "minimal"
        },
        "text": {
            "verbosity": "low"
        },
        "max_output_tokens": 100
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print(f"\nResponse Body:")
print(json.dumps(response.json(), indent=2))

if response.status_code != 200:
    print("\n❌ API Error!")
else:
    print("\n✅ API Success!")
    result = response.json()
    print(f"\nTop-level keys: {list(result.keys())}")
