#!/bin/sh
# Creates and migrates Temporal's Postgres databases. Safe to re-run.
set -eu
TOOL="temporal-sql-tool --plugin postgres12 --ep ${POSTGRES_SEEDS} -p ${DB_PORT:-5432} -u ${POSTGRES_USER} --pw ${POSTGRES_PWD}"
SCHEMA_DIR=/etc/temporal/schema/postgresql/v12

for i in $(seq 1 30); do nc -z "${POSTGRES_SEEDS}" "${DB_PORT:-5432}" && break; sleep 1; done

for db in temporal temporal_visibility; do
  if [ "$db" = temporal ]; then dir=temporal; else dir=visibility; fi
  $TOOL --db "$db" create-database 2>/dev/null || echo "database $db already exists"
  $TOOL --db "$db" setup-schema -v 0.0 2>/dev/null || echo "schema for $db already initialised"
  $TOOL --db "$db" update-schema -d "$SCHEMA_DIR/$dir/versioned"
done
echo "temporal schema ready"
