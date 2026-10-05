#!/usr/bin/env bash
# Serverni ishga tushirish (rivojlantirish rejimi).
set -e
cd "$(dirname "$0")"
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
