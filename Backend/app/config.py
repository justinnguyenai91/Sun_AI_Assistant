import os

EXTERNAL_API_BASE_URL = os.getenv("EXTERNAL_API_BASE_URL")
EXTERNAL_API_PREFIX = os.getenv("EXTERNAL_API_PREFIX")
EXTERNAL_API_TOKEN = os.getenv("EXTERNAL_API_TOKEN")

if not EXTERNAL_API_BASE_URL:
    raise RuntimeError("Missing EXTERNAL_API_BASE_URL")

if not EXTERNAL_API_PREFIX:
    raise RuntimeError("Missing EXTERNAL_API_PREFIX")

# EXTERNAL_API_TOKEN is optional:
# - In local/dev you may set a default token via env.
# - In service mode, MES can supply a token per request.
