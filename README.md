# Tiendix - Tu negocio, tu control, tu Tiendix

Simple Flask application for managing quotations, orders and invoices.

Key features:

- Company logo upload used across all generated PDFs
- QR codes on documents linking back to their online copies
- Responsive TailwindCSS layout with sidebar navigation
- Multi-tenant architecture isolating data per company

## Configuration

Create a `.env` file in the project root and define:

```
SECRET_KEY=replace_with_random_string
```

This value secures Flask sessions.

## Multi-tenant usage

Each table stores a `company_id` and regular users with role `company` only access their own data. Administrators can manage any tenant by selecting an enterprise from the **Empresas** panel.

## AI Recommendations

An experimental endpoint `/api/recommendations` returns the top-selling products as basic "AI" suggestions.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
