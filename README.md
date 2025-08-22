# Application Tada

Simple Flask application for managing quotations, orders and invoices.

## Configuration

Create a `.env` file in the project root and define:

```
SECRET_KEY=replace_with_random_string
```

This value secures Flask sessions.

## AI Recommendations

An experimental endpoint `/api/recommendations` returns the top-selling products as basic "AI" suggestions.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
