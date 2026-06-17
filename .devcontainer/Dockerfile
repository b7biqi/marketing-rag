# Python 3.12 — has wheels for onnxruntime/fastembed/pymupdf (3.14 does not yet).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# libgomp1: required by onnxruntime (fastembed). build-essential/git for any source builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install deps at build time so the image is cached and `create` is fast.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
