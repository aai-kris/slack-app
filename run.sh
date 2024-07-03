#!/bin/sh
export SSL_CERT_FILE=$(python -m certifi)
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
