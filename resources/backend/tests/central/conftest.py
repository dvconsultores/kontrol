"""Mundo de pruebas de la Autoridad Central: base propia (SQLite en memoria o PostgreSQL con `KONTROL_TEST_DB_URL`),
clave de firma SINTÉTICA por módulo, `Settings` construida sin leer el entorno real."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# La API (`central_authority.main`) construye la app al importarse y lee `Settings` del entorno:
# aquí una base en memoria y entorno `qa`, nunca producción. Las pruebas que necesitan ajustes
# concretos construyen `Settings(_env_file=None, ...)` sin leer el entorno.
os.environ.setdefault("KONTROL_CENTRAL_DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("KONTROL_CENTRAL_ENVIRONMENT", "qa")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy.orm import Session, sessionmaker

from central_authority.config import Settings
from central_authority.models import Base
from tests.conftest import make_engine


def pem_privada(clave: Ed25519PrivateKey) -> str:
    return clave.private_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()).decode()


def pem_publica(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def es_postgres() -> bool:
    return os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")


@pytest.fixture
def propietario() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
def ajustes(propietario: Ed25519PrivateKey) -> Settings:
    return Settings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:",
                    signing_private_key_pem=pem_privada(propietario), signing_kid="kontrol-lic-2026-01")


@pytest.fixture
def factoria() -> Iterator[sessionmaker]:
    motor = make_engine()
    Base.metadata.create_all(motor)
    yield sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    Base.metadata.drop_all(motor)
