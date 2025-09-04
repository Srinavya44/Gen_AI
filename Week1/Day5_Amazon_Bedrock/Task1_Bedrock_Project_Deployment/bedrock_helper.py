# bedrock_helper.py
import os
import json
import boto3

# Config
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

client = boto3.client("bedrock-runtime", region_name=REGION)

def call_bedrock(prompt: str, max_tokens: int = 800, temperature: float = 0.2):
    """
    Calls AWS Bedrock with Meta Llama 3 8B Instruct.
    Adjusted for correct payload format: prompt, max_gen_len, temperature.
    """
    payload = {
        "prompt": prompt,
        "max_gen_len": max_tokens,      # Token limit
        "temperature": temperature,     # Creativity level
        "top_p": 0.9                     # Sampling diversity (optional)
    }

    resp = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8")
    )

    body_bytes = resp["body"].read()
    body_text = body_bytes.decode("utf-8")

    # Llama 3 returns JSON with a 'generation' key
    try:
        parsed = json.loads(body_text)
        return parsed.get("generation") or body_text
    except Exception:
        return body_text
