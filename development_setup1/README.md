---
title: eta-fastapi-optimized
emoji: ⚡
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🚀 ETA FastAPI Optimized

This is an optimized FastAPI service deployed on Hugging Face Spaces.

## ⚡ Key Features

- Ultra-fast response (< 5 seconds)
- No heavy ML models
- Rule-based processing for energy spike detection
- Production-ready architecture

## 📌 API Endpoints

### GET /
Check service status

### POST /predict

#### Request:
```json
{
  "question": "Show top unusual energy spikes"
}