"""Arnés de las pruebas del montaje de orquestación: nada toca el `~/.claude.json` real."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import set_deepseek_key as montaje  # noqa: E402


def clave_falsa(letra: str = "a") -> str:
    """Con forma de clave real, pero compuesta al vuelo: el código fuente no la contiene."""
    return "sk-" + letra * 32


@pytest.fixture
def casa(tmp_path, monkeypatch):
    """Un `~/.claude.json` y un `npx` de mentira, con la misma forma que los reales."""
    bin_dir = tmp_path / "node" / "bin"
    lib_dir = tmp_path / "node" / "lib"
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir()
    (lib_dir / "npx-cli.js").write_text("#!/usr/bin/env node\n")
    (lib_dir / "npx-cli.js").chmod(0o755)
    (bin_dir / "npx").symlink_to(lib_dir / "npx-cli.js")
    monkeypatch.setattr(montaje.shutil, "which", lambda nombre: str(bin_dir / "npx") if nombre == "npx" else None)

    fichero = tmp_path / ".claude.json"
    monkeypatch.setattr(montaje, "CLAUDE_JSON", fichero)
    monkeypatch.setattr(montaje, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.delenv(montaje.KEY_NAME, raising=False)

    def aviso_prohibido(*_):
        raise AssertionError("no debía pedirse la clave por el aviso")

    monkeypatch.setattr(montaje.getpass, "getpass", aviso_prohibido)

    class Casa:
        ruta = fichero
        npx = str(bin_dir / "npx")
        proyecto = str(tmp_path / "Kontrol")
        otro = str(tmp_path / "Otro")
        respaldos = tmp_path / "backups"

        def escribir(self, datos: dict) -> None:
            fichero.write_text(json.dumps(datos, indent=2))

        def leer(self) -> dict:
            return json.loads(fichero.read_text())

        def servidor(self, proyecto: str | None = None) -> dict:
            return self.leer()["projects"][proyecto or self.proyecto]["mcpServers"][montaje.SERVER_NAME]

    for carpeta in (Casa.proyecto, Casa.otro):
        Path(carpeta).mkdir()
    return Casa()
