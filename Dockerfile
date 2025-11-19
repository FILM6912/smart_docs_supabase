FROM python:3.13-slim AS base

WORKDIR /app

COPY src /app/src
COPY requirements.txt /app/requirements.txt
COPY .env /app/.env
COPY main.py /app/main.py

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

