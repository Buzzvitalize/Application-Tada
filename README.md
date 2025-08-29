# Tiendix - Tu negocio, tu control, tu Tiendix

Simple Flask application for managing quotations, orders and invoices.

Key features:

- Company logo upload used across all generated PDFs
- QR codes on documents linking back to their online copies
- Responsive TailwindCSS layout with sidebar navigation
- Multi-tenant architecture isolating data per company
- Local RNC catalogue (`data/DGII_RNC.TXT`) auto-completes company names when entering tax IDs
- PDFs generated with FPDF using a simple modern template for quotations, orders and invoices
- Optional document notes stored with quotations and carried over to orders and invoices, appearing on generated PDFs
- PDF exports display document numbers and invoice type (Consumidor Final o Crédito Fiscal)
- Quotation form reuses existing clients and products via auto-complete fields
- Approved account requests trigger an email notification with login details

The repository does not include a prebuilt `database.sqlite`; each
environment should generate its own database using the migration
commands below.

## Configuration

Copy `.env.example` to `.env` and define a random secret key:

```
SECRET_KEY=replace_with_random_string
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASS=supersecret
SMTP_FROM=tiendix@example.com
```

This value secures Flask sessions and is required for the application to start.

## Multi-tenant usage

Each table stores a `company_id` and regular users with role `company` only access their own data. Administrators can manage any tenant by selecting an enterprise from the **Empresas** panel.

## AI Recommendations

An experimental endpoint `/api/recommendations` returns the top-selling products as basic "AI" suggestions.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask db init  # first run only
flask db migrate -m "initial"
flask db upgrade
python scripts/seed_db.py  # optional: seed admin user and sample data
pytest
python app.py
```

For company name auto-completion, download the latest `DGII_RNC.TXT` from the DGII and place it under `data/`.
