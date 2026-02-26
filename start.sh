#!/usr/bin/env bash
# This ensures Render uses the correct PORT
uvicorn main:app --host 0.0.0.0 --port $PORT
