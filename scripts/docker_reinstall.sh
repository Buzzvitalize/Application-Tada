#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "[error] Docker no está instalado o no está en PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[error] Docker Compose plugin no está disponible (docker compose)." >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "[info] No existe .env, creando desde .env.example"
  cp .env.example .env
  echo "[warn] Revisa .env y cambia SECRET_KEY antes de producción."
fi

echo "[step] Deteniendo y borrando stack/volúmenes previos..."
docker compose down -v --remove-orphans

echo "[step] Reconstruyendo imagen..."
docker compose build --no-cache

echo "[step] Levantando servicio..."
docker compose up -d

echo "[ok] Reinstalación Docker completada."
echo "[next] Ver logs: docker compose logs -f web"
echo "[next] URL: http://localhost:5000"
