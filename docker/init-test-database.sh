#!/bin/sh
set -eu

if ! psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align \
  --command "SELECT 1 FROM pg_database WHERE datname = 'marketplace_test'" | grep -q 1; then
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --command "CREATE DATABASE marketplace_test"
fi
