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
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=user@example.com
MAIL_PASSWORD=supersecret
MAIL_DEFAULT_SENDER=tiendix@example.com
```

This value secures Flask sessions and is required for the application to start.

## Multi-tenant usage

Each table stores a `company_id` and regular users with role `company` only access their own data. Administrators can manage any tenant by selecting an enterprise from the **Empresas** panel.

## AI Recommendations

An experimental endpoint `/api/recommendations` returns the top-selling products as basic "AI" suggestions.


## Docker deployment

You can run the project in Docker with SQLite persistence and uploads persistence:

1. **Prepare environment variables**

   Create a `.env` file next to `docker-compose.yml` (or export vars in your shell):

   ```env
   SECRET_KEY=your_long_random_secret
   MAIL_SERVER=smtp.example.com
   MAIL_PORT=587
   MAIL_USERNAME=user@example.com
   MAIL_PASSWORD=supersecret
   MAIL_DEFAULT_SENDER=tiendix@example.com
   ```

2. **Build and start containers**

   ```bash
   docker compose up -d --build
   ```

3. **Open the app**

   - URL: `http://localhost:5000`

4. **(Optional) seed initial data**

   ```bash
   docker compose exec web python scripts/seed_db.py
   ```

5. **See logs / stop service**

   ```bash
   docker compose logs -f web
   docker compose down
   ```

### How this Docker setup works

- `Dockerfile` builds a Python 3.11 image with dependencies needed by Flask and WeasyPrint.
- `docker-compose.yml` runs the app as service `web` on port `5000`.
- `APP_CONFIG=production` switches the app to `ProductionConfig`.
- `DATABASE_URL=sqlite:////data/database.sqlite` stores the DB in the named volume `tiendix_data`.
- Uploaded logos/files are stored in `tiendix_uploads` mounted at `/app/static/uploads`.

### Deploying to a server (quick procedure)

1. Install Docker + Docker Compose plugin on the server.
2. Copy project files to server (`git clone ...`).
3. Create `.env` with production values (`SECRET_KEY`, mail settings).
4. Run `docker compose up -d --build`.
5. Put Nginx/Caddy in front (optional but recommended) for HTTPS and custom domain.

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
