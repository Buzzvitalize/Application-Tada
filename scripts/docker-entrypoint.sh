#!/usr/bin/env sh
set -e

echo "[entrypoint] Aplicando migraciones..."
flask --app app db upgrade

echo "[entrypoint] Iniciando aplicación..."
exec "$@"
