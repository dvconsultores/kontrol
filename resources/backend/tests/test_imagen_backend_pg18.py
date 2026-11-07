"""Pruebas estáticas de la imagen backend: cliente PostgreSQL 18 fijado (T053)."""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOCKERFILE = (RAIZ / "Dockerfile.backend").read_text(encoding="utf-8")
COMPOSE = (RAIZ / "compose.yaml").read_text(encoding="utf-8")


def test_cliente_18_con_version_exacta() -> None:
    assert "postgresql-client-18=18.6-1.pgdg13+2" in DOCKERFILE


def test_libpq_con_version_exacta() -> None:
    assert "libpq5=18.6-1.pgdg13+2" in DOCKERFILE


def test_no_se_instala_servidor() -> None:
    texto = DOCKERFILE.replace("postgresql-client-18", "")
    assert re.search(r"\bpostgresql-\d+\b(?!-)", texto) is None
    assert "postgresql-common" not in DOCKERFILE


def test_clave_fijada_por_sha256() -> None:
    assert "0144068502a1eddd2a0280ede10ef607d1ec592ce819940991203941564e8e76" in DOCKERFILE
    assert "sha256sum -c" in DOCKERFILE


def test_repositorio_con_prioridad_baja() -> None:
    assert "Pin-Priority: 100" in DOCKERFILE
    assert "signed-by=/etc/apt/keyrings/pgdg.asc" in DOCKERFILE


def test_la_construccion_comprueba_la_version() -> None:
    assert "pg_dump --version" in DOCKERFILE
    assert "pg_restore --version" in DOCKERFILE


def test_la_base_no_cambia() -> None:
    primera_from = next(
        linea for linea in DOCKERFILE.splitlines() if linea.startswith("FROM")
    )
    assert primera_from.startswith("FROM python:3.13.16-slim-trixie@sha256:")


def test_compose_declara_destinos() -> None:
    assert "kontrol-backup-destinations:/data/backup-destinations" in COMPOSE
    assert "KONTROL_BACKUP_DESTINATIONS_PATH" in COMPOSE


def test_compose_no_declara_la_clave_en_el_backend() -> None:
    assert "KONTROL_BACKUP_KEY" not in COMPOSE
