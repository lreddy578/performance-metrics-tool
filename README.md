# Performance Metrics Tool

A FastAPI web app for tracking SDET performance metrics.

## Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv .venv`
3. Activate: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file (see `.env.example`)
6. Run: `uvicorn app:app --reload`

## Stack
- **Backend**: FastAPI + Python
- **Storage**: JSON files
- **Auth**: JWT (username/password)
- **Frontend**: HTML/CSS/JS