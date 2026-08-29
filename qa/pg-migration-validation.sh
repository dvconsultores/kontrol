#!/usr/bin/env bash
# Validación de migraciones sobre PostgreSQL real (Spec 045 · CVG-045-01/02).
#   Caso A: base limpia -> alembic upgrade head -> current/heads/check
#   Caso B: base pre-045 con datos -> upgrade head -> preservación
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/resources/backend"
PGBIN="$BACKEND/.venv/lib/python3.11/site-packages/pgserver/pginstall/bin"
PORT="${KONTROL_PGPORT:-55432}"
export KONTROL_SECRET_KEY=test-secret-key-0123456789abcdef0123456789abcdef
export KONTROL_ENVIRONMENT=local KONTROL_LOG_JSON=false KONTROL_COOKIE_SECURE=false
export KONTROL_INSTALLATION_VOLUME_PATH=/tmp/k-lic KONTROL_STORAGE_PATH=/tmp/k-st KONTROL_BACKUP_PATH=/tmp/k-bk
cd "$BACKEND"
url() { echo "postgresql+psycopg2://kontrol_migrator:qa@localhost:$PORT/$1"; }
psql_() { "$PGBIN/psql" -h localhost -p "$PORT" -U kontrol_migrator -d "$1" "${@:2}"; }

echo "########## CASO A · base limpia"
bash "$ROOT/qa/pg-provision.sh" mkdb kontrol_clean >/dev/null
KONTROL_DB_URL="$(url kontrol_clean)" .venv/bin/alembic upgrade head 2>&1 | tail -1
echo "-- current --"; KONTROL_DB_URL="$(url kontrol_clean)" .venv/bin/alembic current 2>/dev/null | tail -1
echo "-- heads   --"; KONTROL_DB_URL="$(url kontrol_clean)" .venv/bin/alembic heads 2>/dev/null | tail -1
echo "-- tablas  --"; psql_ kontrol_clean -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
echo "-- drift (alembic check) --"
KONTROL_DB_URL="$(url kontrol_clean)" .venv/bin/alembic check 2>&1 \
  | grep "alembic.autogenerate.compare" | sed 's/.*compare\] //' | sort -u || echo "sin drift"

echo
echo "########## CASO B · base anterior a 045, con datos"
bash "$ROOT/qa/pg-provision.sh" mkdb kontrol_pre045 >/dev/null
KONTROL_DB_URL="$(url kontrol_pre045)" .venv/bin/alembic upgrade 0014_numeric_money_2 >/dev/null 2>&1
psql_ kontrol_pre045 -q -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO installations (id, installation_uuid, state, created_at, updated_at)
  VALUES ('inst-1','uuid-1','ACTIVE',now(),now());
INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at)
  VALUES ('ten-1','inst-1','DEMO','Demo','MULTI_COMPANY','ACTIVE',now(),now());
INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, status, created_at, updated_at)
  VALUES ('co-1','ten-1','D1','Demo CA','J-1','CA','VED','ACTIVE',now(),now());
INSERT INTO roles (id, code, name, protected, status, created_at, updated_at)
  VALUES ('role-admin','ADMIN','Administrador',true,'ACTIVE',now(),now());
INSERT INTO users (id, tenant_id, username, email, password_hash, status, mfa_enabled, must_change_password, failed_attempts, created_at, updated_at)
  VALUES ('u-1','ten-1','admin','a@d.com','x','ACTIVE',false,false,0,now(),now());
INSERT INTO user_roles (id, user_id, role_id, created_at, updated_at) VALUES ('ur-1','u-1','role-admin',now(),now());
-- Histórico legado: 3 con empresa válida y 1 con referencia colgante
INSERT INTO approval_requests (id, company_id, object_ref, requester_id, amount, decision, status, created_at, updated_at) VALUES
 ('leg-1','co-1','DESP-0001','u-1',1500.00,'APPROVED','APPROVED',now(),now()),
 ('leg-2','co-1','DESP-0002','u-1',2500.00,'REJECTED','REJECTED',now(),now()),
 ('leg-3','co-1','DESP-0003','u-1',900.00,NULL,'PENDING',now(),now()),
 ('leg-4','co-BORRADA','DESP-0004','u-1',100.00,'APPROVED','APPROVED',now(),now());
SQL
echo "-- ANTES --"; psql_ kontrol_pre045 -tAc "SELECT 'approval_requests(legado)='||count(*) FROM approval_requests;"
KONTROL_DB_URL="$(url kontrol_pre045)" .venv/bin/alembic upgrade head 2>&1 | grep -E "^\[0016\]" || true
echo "-- DESPUÉS --"
psql_ kontrol_pre045 -tAc "
SELECT 'legada renombrada = '||count(*) FROM regulatory_approval_requests;
SELECT 'motor (migradas)  = '||count(*) FROM approval_requests;
SELECT 'permisos aprobaciones = '||count(*) FROM permissions WHERE resource='aprobaciones';
SELECT 'role_permissions ADMIN = '||count(*) FROM role_permissions WHERE role_id='role-admin';"
echo "-- datos legados preservados --"
psql_ kontrol_pre045 -tAc "SELECT id||' | '||object_ref||' | '||amount||' | '||coalesce(decision,'—')||' | '||status FROM regulatory_approval_requests ORDER BY id;"
echo "-- migrado al motor --"
psql_ kontrol_pre045 -tAc "SELECT document_id||' | '||status||' | '||policy_version||' | '||amount_base FROM approval_requests ORDER BY document_id;"
echo "-- índices sin colisión --"
psql_ kontrol_pre045 -tAc "SELECT indexname FROM pg_indexes WHERE tablename IN ('approval_requests','regulatory_approval_requests') ORDER BY 1;"
