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

Sí, ya quedó adaptado para Docker y aquí te dejo el procedimiento completo en español.

### 1) Prerrequisitos

- Docker Engine instalado
- Docker Compose plugin (`docker compose`)

Verificación rápida:

```bash
docker --version
docker compose version
```

### 2) Variables de entorno

Crea un archivo `.env` (en la raíz del proyecto) a partir de `.env.example`:

```env
SECRET_KEY=tu_clave_larga_y_segura
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=user@example.com
MAIL_PASSWORD=supersecret
MAIL_DEFAULT_SENDER=tiendix@example.com
APP_CONFIG=production
DATABASE_URL=sqlite:////data/database.sqlite
```

### 3) Construir y levantar

```bash
docker compose up -d --build
```

Qué pasa internamente:
- Se construye la imagen desde `Dockerfile`.
- El contenedor ejecuta `scripts/docker-entrypoint.sh`.
- El entrypoint corre `flask db upgrade` automáticamente.
- Luego inicia la app con Gunicorn en el puerto 5000.

### 4) Abrir la aplicación

- URL: `http://localhost:5000`

### 5) (Opcional) Cargar datos iniciales

```bash
docker compose exec web python scripts/seed_db.py
```

### 6) Comandos útiles de operación

```bash
# Ver logs en tiempo real
docker compose logs -f web

# Reiniciar servicio
docker compose restart web

# Detener contenedores
docker compose down

# Detener y borrar volúmenes (ELIMINA DB/upload persistidos)
docker compose down -v
```

### 7) Persistencia de datos

El `docker-compose.yml` ya define volúmenes:
- `tiendix_data` → `/data` (SQLite)
- `tiendix_uploads` → `/app/static/uploads` (logos/archivos)

Por eso, aunque recrees el contenedor, la información se mantiene.

### 8) Subir tu imagen a Docker Hub (opcional)

```bash
# 1) Login
docker login

# 2) Build con tag de tu usuario
docker build -t TUUSUARIO/tiendix:latest .

# 3) Push
docker push TUUSUARIO/tiendix:latest
```

Luego, en un servidor, puedes usar esa imagen directamente en `docker-compose.yml` reemplazando `build: .` por `image: TUUSUARIO/tiendix:latest`.

### 9) Despliegue recomendado en servidor

1. Instala Docker + Compose.
2. Copia `docker-compose.yml` y `.env` al servidor.
3. Ejecuta `docker compose up -d`.
4. Coloca Nginx/Caddy como reverse proxy para HTTPS y dominio.
5. Configura backups del volumen `tiendix_data`.

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
