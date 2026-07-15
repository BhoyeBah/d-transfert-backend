#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/db_restore.sh <backup_file>

Variables utiles:
  COMPOSE_FILE            Chemin vers docker-compose.prod.yml
  ENV_FILE                Fichier d'environnement de production
  RESTORE_FORCE=1         Désactive la confirmation interactive
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHELL_COMPOSE_FILE="${COMPOSE_FILE:-}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"
backup_file="$1"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier d'environnement introuvable: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

COMPOSE_FILE="${SHELL_COMPOSE_FILE:-${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}}"

if [[ ! -f "$backup_file" ]]; then
  echo "Sauvegarde introuvable: $backup_file" >&2
  exit 1
fi

echo "Attention: la restauration remplace les donnees actuelles de la base."
echo "Pense a stopper les ecritures applicatives pendant l'operation."

if [[ "${RESTORE_FORCE:-0}" != "1" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Tape YES_RESTORE pour continuer: " confirmation
    if [[ "$confirmation" != "YES_RESTORE" ]]; then
      echo "Restauration annulee."
      exit 1
    fi
  else
    echo "RESTORE_FORCE=1 requis pour une restauration non interactive." >&2
    exit 1
  fi
fi

gunzip -c "$backup_file" | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres sh -lc '
  set -euo pipefail
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_restore --clean --if-exists --no-owner --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB"
'

echo "Restauration terminee avec succes."
