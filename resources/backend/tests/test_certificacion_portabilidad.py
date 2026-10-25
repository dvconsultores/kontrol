"""CRP · Portabilidad del anfitrión de certificación (Spec 054 · CERTIFICATION-HOST-PORTABILITY)."""

import argparse
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))
import certificacion_release as cr  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]


def _contexto(
    tmp_path: Path, **opciones: object
) -> cr.Contexto:
    """Construye un contexto de prueba aislado en un directorio temporal."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    opciones_por_defecto: dict[str, object] = {
        "incluir_v0_historico": False,
        "espera_salud_min": cr.ESPERA_SALUD_MIN_POR_DEFECTO,
        "conservar_espacio": True,
        "solo_preflight": False,
    }
    opciones_por_defecto.update(opciones)
    espacio = cr.crear_espacio(home, "RUN1")
    evidencia = tmp_path / "evidencia"
    evidencia.mkdir(parents=True)
    return cr.Contexto(
        run_id="RUN1",
        opciones=argparse.Namespace(**opciones_por_defecto),
        home=home,
        espacio=espacio,
        evidencia=evidencia,
        raices=cr.raices_a_sanear(os.environ, home),
        manifiesto=cr.manifiesto_inicial(
            "RUN1", argparse.Namespace(**opciones_por_defecto), [], []
        ),
    )


def _git_env(tmp_path: Path) -> dict[str, str]:
    """Entorno aislado para invocar git en las pruebas de CRP-07."""
    return {
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "PATH": os.environ.get("PATH", ""),
    }


def _git(
    tmp_path: Path,
    directorio: Path,
    *args: str,
    input: bytes | None = None,
) -> str:
    """Ejecuta git de forma reproducible y sin configuraciones del anfitrión."""
    git = shutil.which("git")
    assert git is not None, "git no está disponible en PATH"
    resultado = subprocess.run(
        [git, "-c", "user.email=qa@example.invalid", "-c", "user.name=qa", *args],
        cwd=directorio,
        env=_git_env(tmp_path),
        input=input,
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout.strip()


def test_crp_01_orden_de_e2e_pin_workers_y_reintentos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CRP-01: la orden de E2E fija 6 workers y 0 reintentos sin depender de la CPU."""
    assert cr.E2E_WORKERS_CANONICOS == 6
    assert cr.E2E_REINTENTOS_CANONICOS == 0

    py_c = "/opt/qa/bin/python"
    py_r = "/opt/producto/bin/python"
    esperado = [
        py_c,
        str(cr.E2E_RUN),
        "--con-analizador",
        "--python-de-producto",
        py_r,
        "--",
        "--workers=6",
        "--retries=0",
    ]

    original_cpu_count = os.cpu_count
    original_sched_getaffinity = getattr(os, "sched_getaffinity", None)
    try:
        monkeypatch.setattr(os, "cpu_count", lambda: 2)
        if original_sched_getaffinity is not None:
            monkeypatch.setattr(os, "sched_getaffinity", lambda *args, **kwargs: set(range(2)))
        assert cr.orden_de_e2e(py_c, py_r) == esperado

        monkeypatch.setattr(os, "cpu_count", lambda: 64)
        if original_sched_getaffinity is not None:
            monkeypatch.setattr(
                os, "sched_getaffinity", lambda *args, **kwargs: set(range(64))
            )
        assert cr.orden_de_e2e(py_c, py_r) == esperado
    finally:
        os.cpu_count = original_cpu_count
        if original_sched_getaffinity is not None:
            os.sched_getaffinity = original_sched_getaffinity


def test_crp_02_verificar_perfil_e2e_acepta_6_workers_solamente() -> None:
    """CRP-02: solo un perfil de 6 workers se acepta; otros perfiles fallan."""
    log_valido = (
        "inicio de suite\n"
        "Running 284 tests using 6 workers\n"
        "[chromium] › especificacion.spec.ts:42:3 › paso (12ms)\n"
        "final de suite\n"
    )
    assert cr.verificar_perfil_e2e(log_valido) == {"workers": 6, "retries": 0}

    log_12_workers = "Running 284 tests using 12 workers\n"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.verificar_perfil_e2e(log_12_workers)

    log_1_worker = "Running 1 test using 1 worker\n"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.verificar_perfil_e2e(log_1_worker)

    log_sin_linea = "suite completa sin linea de playwright\n"
    with pytest.raises(cr.FalloDeCertificacion):
        cr.verificar_perfil_e2e(log_sin_linea)


def test_crp_03_estructura_etapas_usa_politicas() -> None:
    """CRP-03: las etapas invocan la política de entorno, el árbol y el perfil E2E."""
    fuente_preflight = inspect.getsource(cr.etapa_preflight)
    assert "comprobar_politica_de_entorno(" in fuente_preflight
    indice_politica = fuente_preflight.index("comprobar_politica_de_entorno(")
    indice_which = fuente_preflight.find("shutil.which(")
    assert indice_which == -1 or indice_politica < indice_which
    assert "arbol_certificado(" in fuente_preflight

    fuente_e2e = inspect.getsource(cr.etapa_e2e)
    assert "orden_de_e2e(" in fuente_e2e
    assert "verificar_perfil_e2e(" in fuente_e2e


def test_crp_04_entorno_de_sujeto_limpia_y_conserva(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CRP-04: el entorno del sujeto elimina CI, secretos y Python; conserva lo permitido."""
    base = {
        "CI": "true",
        "PATH": "/usr/bin",
        "GITHUB_TOKEN": "t0k3n-sintetico",
        "PYTHONPATH": "/x",
        "LANG": "C.UTF-8",
        "EDITOR": "vi",
    }
    resultado = cr.entorno_de_sujeto(base, extra={"PATH": "/otro"})
    assert "CI" not in resultado
    assert "GITHUB_TOKEN" not in resultado
    assert "PYTHONPATH" not in resultado
    assert resultado["PATH"] == "/otro"
    assert resultado["LANG"] == "C.UTF-8"
    assert resultado["EDITOR"] == "vi"
    assert resultado["PYTHONDONTWRITEBYTECODE"] == "1"


@pytest.mark.parametrize(
    ("nombre", "clase_esperada"),
    [
        ("CI", "CANONICALIZED"),
        ("PYTHONPATH", "CANONICALIZED"),
        ("VIRTUAL_ENV", "CANONICALIZED"),
        ("PATH", "ALLOWED_INHERITED"),
        ("HOME", "ALLOWED_INHERITED"),
        ("LC_ALL", "ALLOWED_INHERITED"),
        ("PLAYWRIGHT_BROWSERS_PATH", "ALLOWED_INHERITED"),
        ("PYTHONIOENCODING", "ALLOWED_INHERITED"),
        ("KONTROL_CLAMSCAN_PATH", "ALLOWED_INHERITED"),
        ("KONTROL_QA_CERT_HOME", "ALLOWED_INHERITED"),
        ("PYTEST_ADDOPTS", "FORBIDDEN"),
        ("PWDEBUG", "FORBIDDEN"),
        ("PWTEST_X", "FORBIDDEN"),
        ("PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS", "FORBIDDEN"),
        ("PYTHONWARNINGS", "FORBIDDEN"),
        ("NODE_OPTIONS", "FORBIDDEN"),
        ("NODE_ENV", "FORBIDDEN"),
        ("LD_PRELOAD", "FORBIDDEN"),
        ("UV_INDEX_URL", "FORBIDDEN"),
        ("PIP_INDEX_URL", "FORBIDDEN"),
        ("npm_config_registry", "FORBIDDEN"),
        ("COVERAGE_PROCESS_START", "FORBIDDEN"),
        ("PGPASSWORD", "FORBIDDEN"),
        ("KONTROL_PGDATA", "FORBIDDEN"),
        ("KONTROL_SECRET_KEY", "FORBIDDEN"),
        ("GIT_DIR", "FORBIDDEN"),
        ("GIT_INDEX_FILE", "FORBIDDEN"),
        ("GIT_WORK_TREE", "FORBIDDEN"),
        ("GIT_CONFIG_COUNT", "FORBIDDEN"),
        ("GIT_CONFIG_GLOBAL", "FORBIDDEN"),
        ("GIT_EDITOR", "IRRELEVANT"),
        ("GIT_PAGER", "IRRELEVANT"),
        ("GIT_ASKPASS", "IRRELEVANT"),
        ("GITHUB_TOKEN", "SECRET"),
        ("MY_API_KEY", "SECRET"),
        ("aws_access_key_id", "SECRET"),
        ("PWD", "IRRELEVANT"),
        ("EDITOR", "IRRELEVANT"),
        ("SSH_AUTH_SOCK", "IRRELEVANT"),
    ],
)
def test_crp_05_clasificar_entorno_clasifica_cada_nombre(
    nombre: str, clase_esperada: str
) -> None:
    """CRP-05: cada variable se clasifica con la precedencia especificada."""
    resultado = cr.clasificar_entorno({nombre: "valor-sintetico"})
    clases = list(resultado.keys())
    assert clases == [
        "CANONICALIZED",
        "ALLOWED_INHERITED",
        "FORBIDDEN",
        "SECRET",
        "IRRELEVANT",
    ]
    assert nombre in resultado[clase_esperada]
    for lista in resultado.values():
        assert lista == sorted(lista)


def test_crp_06_comprobar_politica_de_entorno_rechaza_prohibidas() -> None:
    """CRP-06: las variables prohibidas fallan con el detalle adecuado y sin valores."""
    entorno = {
        "PATH": "/usr/bin",
        "PYTEST_ADDOPTS": "-x",
        "NODE_OPTIONS": "--require x",
        "GITHUB_TOKEN": "s3cr3t-valor",
    }
    with pytest.raises(cr.FalloDePreflight) as excinfo:
        cr.comprobar_politica_de_entorno(entorno)
    detalle = excinfo.value.detalle
    assert detalle["prohibidas"] == ["NODE_OPTIONS", "PYTEST_ADDOPTS"]
    serializado = json.dumps(detalle)
    assert "s3cr3t-valor" not in serializado
    assert "-x" not in serializado
    assert "--require x" not in serializado


def test_crp_06_comprobar_politica_de_entorno_describe_entorno_valido() -> None:
    """CRP-06: la política describe el entorno canónico sin incluir valores."""
    entorno = {
        "PATH": "/usr/bin",
        "CI": "true",
        "GITHUB_TOKEN": "s3cr3t-valor",
        "EDITOR": "vi",
    }
    resultado = cr.comprobar_politica_de_entorno(entorno)
    assert resultado["version"] == 1
    assert resultado["canonicalizadas"] == ["CI"]
    assert resultado["heredadas_permitidas"] == ["PATH"]
    assert resultado["prohibidas"] == []
    assert resultado["secretas"] == ["GITHUB_TOKEN"]
    assert resultado["irrelevantes"] == 1
    serializado = json.dumps(resultado)
    assert "s3cr3t-valor" not in serializado
    assert "/usr/bin" not in serializado
    assert "true" not in serializado
    assert "vi" not in serializado


def _repo_de_prueba(tmp_path: Path) -> Path:
    """Crea un repositorio git temporal con la estructura documental de la Spec."""
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "specs" / "001" / "evidence").mkdir(parents=True)
    (repo / "docs" / "roadmap").mkdir(parents=True)
    (repo / "docs" / "governance").mkdir(parents=True)
    (repo / "requerimientos").mkdir(parents=True)
    (repo / "conf").mkdir(parents=True)

    (repo / "app" / "main.py").write_text("# main v1\n")
    (repo / "specs" / "001" / "spec.md").write_text("# spec v1\n")
    (repo / "specs" / "001" / "evidence" / "e.md").write_text("# evidence v1\n")
    (repo / "docs" / "roadmap" / "r.md").write_text("# roadmap v1\n")
    (repo / "docs" / "governance" / "adr.md").write_text("# adr v1\n")
    (repo / "requerimientos" / "fuente.md").write_text("# fuente v1\n")
    (repo / ".gitignore").write_text(".env\n")

    _git(tmp_path, repo, "init")
    _git(tmp_path, repo, "add", "-A")
    _git(tmp_path, repo, "commit", "-m", "estado inicial")
    return repo


def _snapshot_repo(repo: Path) -> tuple[bytes, set[str]]:
    """Captura el índice y las rutas de objetos del repositorio."""
    indice = (repo / ".git" / "index").read_bytes()
    objetos = {
        str(ruta.relative_to(repo / ".git" / "objects"))
        for ruta in (repo / ".git" / "objects").rglob("*")
        if ruta.is_file()
    }
    return indice, objetos


def _ctx_con_git(tmp_path: Path) -> cr.Contexto:
    """Construye un contexto con la herramienta git configurada."""
    ctx = _contexto(tmp_path)
    ctx.datos = {"herramientas": {"git": shutil.which("git")}}
    return ctx


def test_crp_07_arbol_certificado_no_toca_el_repositorio(tmp_path: Path) -> None:
    """CRP-07: el árbol certificado aísla el índice real y aplica las exclusiones."""
    repo = _repo_de_prueba(tmp_path)
    ctx = _ctx_con_git(tmp_path)

    def arbol_limpio_esperado() -> str:
        return _git(tmp_path, repo, "rev-parse", "HEAD^{tree}")

    def trabajo_fresco() -> Path:
        trabajo = tmp_path / f"trabajo-{hashlib.sha256(os.urandom(8)).hexdigest()}"
        trabajo.mkdir(parents=True)
        return trabajo

    indice_antes, objetos_antes = _snapshot_repo(repo)

    # (a) árbol limpio
    resultado = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado["arbol"] == arbol_limpio_esperado()
    assert resultado["excluidos_con_cambios"] == []

    # (b) modificación rastreada no excluida cambia el árbol y se restaura
    main_py = repo / "app" / "main.py"
    contenido_original = main_py.read_text()
    main_py.write_text("# main v2\n")
    resultado_modificado = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_modificado["arbol"] != arbol_limpio_esperado()
    main_py.write_text(contenido_original)
    resultado_restaurado = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_restaurado["arbol"] == arbol_limpio_esperado()

    # (c) archivo no rastreado no excluido cambia el árbol
    nuevo_py = repo / "app" / "nuevo.py"
    nuevo_py.write_text("# nuevo\n")
    resultado_nuevo = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_nuevo["arbol"] != arbol_limpio_esperado()
    nuevo_py.unlink()
    resultado_sin_nuevo = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_sin_nuevo["arbol"] == arbol_limpio_esperado()

    # (d) modificaciones en rutas excluidas
    rutas_excluidas = [
        repo / "specs" / "001" / "spec.md",
        repo / "specs" / "001" / "evidence" / "e.md",
        repo / "docs" / "roadmap" / "r.md",
        repo / "requerimientos" / "fuente.md",
    ]
    for ruta in rutas_excluidas:
        ruta.write_text(f"{ruta.name} v2\n")
    extra_excluidos = [
        repo / "requerimientos" / "SNAT.docx",
        repo / "conf" / "clave.pem",
        repo / "conf" / ".env.local",
    ]
    for ruta in extra_excluidos:
        ruta.write_text("sintetico\n")
    resultado_excluido = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_excluido["arbol"] == arbol_limpio_esperado()
    relativas = {
        str(ruta.relative_to(repo)) for ruta in [*rutas_excluidas, *extra_excluidos]
    }
    assert resultado_excluido["excluidos_con_cambios"] == sorted(relativas)

    # (e) modificación rastreada no excluida
    adr = repo / "docs" / "governance" / "adr.md"
    adr.write_text("# adr v2\n")
    resultado_adr = cr.arbol_certificado(ctx, repo, trabajo_fresco())
    assert resultado_adr["arbol"] != arbol_limpio_esperado()

    # (f) el repositorio original no se modifica
    indice_despues, objetos_despues = _snapshot_repo(repo)
    assert indice_despues == indice_antes
    assert objetos_despues == objetos_antes


def test_crp_11_arbol_certificado_ignora_la_configuracion_git_del_anfitrion(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    repo = _repo_de_prueba(tmp_path)
    nuevo_crlf = repo / "app" / "nuevo_crlf.txt"
    nuevo_crlf.write_bytes(b"linea uno\r\nlinea dos\r\n")

    gitconfig_crlf = tmp_path / "gitconfig-crlf"
    gitconfig_crlf.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
    gitconfig_vacio = tmp_path / "gitconfig-vacio"
    gitconfig_vacio.write_text("", encoding="utf-8")

    ctx = _ctx_con_git(tmp_path)

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig_crlf))
    arbol_crlf = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-1")["arbol"]

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig_vacio))
    arbol_vacio = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-2")["arbol"]

    assert arbol_crlf == arbol_vacio


def test_crp_12_arbol_certificado_ignora_filtros_globales_del_anfitrion(tmp_path, monkeypatch):
    """CRP-12: un filtro clean definido en la configuración global del anfitrión no cambia el árbol certificado."""
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo = _repo_de_prueba(tmp_path)
    (repo / ".gitattributes").write_text("*.txt filter=kq\n", encoding="utf-8")
    (repo / "app" / "dato.txt").write_text("aaa\n", encoding="utf-8")
    _git(tmp_path, repo, "add", "-A")
    _git(tmp_path, repo, "commit", "-m", "filtro")
    (repo / "app" / "dato.txt").write_text("aaa bbb\n", encoding="utf-8")
    (tmp_path / "gitconfig-filtro").write_text(
        "[filter \"kq\"]\n\tclean = tr a z\n", encoding="utf-8"
    )
    (tmp_path / "gitconfig-vacio").write_text("", encoding="utf-8")
    ctx = _ctx_con_git(tmp_path)

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig-filtro"))
    arbol_filtro = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-a")["arbol"]

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig-vacio"))
    arbol_vacio = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-b")["arbol"]

    assert arbol_filtro == arbol_vacio


def test_crp_13_arbol_certificado_ignora_ignore_y_attributes_de_xdg(tmp_path, monkeypatch):
    """CRP-13: los ficheros git/ignore y git/attributes por defecto del anfitrión no cambian el árbol certificado."""
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo = _repo_de_prueba(tmp_path)
    (repo / "app" / "nuevo.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "app" / "notas.txt").write_bytes(b"uno\r\ndos\r\n")
    xdg = tmp_path / "xdg"
    (xdg / "git").mkdir(parents=True)
    (xdg / "git" / "ignore").write_text("*.py\n", encoding="utf-8")
    (xdg / "git" / "attributes").write_text("*.txt text\n", encoding="utf-8")
    vacio = tmp_path / "xdg-vacio"
    vacio.mkdir()
    ctx = _ctx_con_git(tmp_path)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    arbol_xdg = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-a")["arbol"]

    monkeypatch.setenv("XDG_CONFIG_HOME", str(vacio))
    arbol_vacio = cr.arbol_certificado(ctx, repo, tmp_path / "fresh-b")["arbol"]

    assert arbol_xdg == arbol_vacio


def test_crp_08_hash_de_entrada_v2_determinista_y_sensible(
    tmp_path: Path,
) -> None:
    """CRP-08: el hash v2 usa la serialización exacta y cambia con cada componente."""
    assert cr.VERSION_HASH_DE_ENTRADA == 2

    valores = {
        "head": "a" * 40,
        "arbol": "b" * 40,
        "digests": {"app": "sha256:" + "c" * 64},
        "locks": {"deps": {"pkg": "1.0.0"}},
        "plataforma": "linux",
        "referencia": "HEAD",
        "postgres_qa": "d" * 64,
    }

    def hash_manual(v: dict[str, object]) -> str:
        serializado = json.dumps(
            {
                "version": 2,
                "head": v["head"],
                "arbol": v["arbol"],
                "politica_del_arbol": 1,
                "digests": dict(v["digests"]),
                "locks": dict(v["locks"]),
                "plataforma": v["plataforma"],
                "referencia": v["referencia"],
                "postgres_qa": v["postgres_qa"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(serializado).hexdigest()

    obtenido = cr.hash_de_entrada(**valores)
    assert obtenido == hash_manual(valores)

    for clave in valores:
        copia = dict(valores)
        copia[clave] = {
            "head": "e" * 40,
            "arbol": "f" * 40,
            "digests": {"otra": "sha256:" + "1" * 64},
            "locks": {"otra": {"pkg": "2.0.0"}},
            "plataforma": "darwin",
            "referencia": "rama-alternativa",
            "postgres_qa": "2" * 64,
        }[clave]
        assert cr.hash_de_entrada(**copia) != obtenido


def _ctx_etapa_manifiesto(tmp_path: Path, arbol_especificado: str) -> cr.Contexto:
    """Prepara un contexto con el hash de árbol proveído por el manifiesto."""
    ctx = _contexto(tmp_path)
    ctx.fallo_previo = True
    ctx.manifiesto["GIT_HEAD"] = "a" * 40
    ctx.manifiesto["CERTIFICATION_INPUT_TREE_HASH"] = arbol_especificado
    return ctx


def test_crp_09_etapa_manifiesto_omite_arbol_si_falta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRP-09: sin árbol en el manifiesto no se recalcula ni se vincula."""
    ctx = _contexto(tmp_path)
    ctx.fallo_previo = True
    ctx.manifiesto["GIT_HEAD"] = "a" * 40
    ctx.manifiesto["CERTIFICATION_INPUT_TREE_HASH"] = "NOT_RUN"
    llamadas: list[Path] = []

    def doble(ctx_interno: cr.Contexto, raiz: Path, trabajo: Path) -> dict[str, object]:
        llamadas.append(raiz)
        return {"arbol": "b" * 40, "excluidos_con_cambios": []}

    monkeypatch.setattr(cr, "arbol_certificado", doble)
    cr.etapa_manifiesto(ctx)
    assert llamadas == []
    assert ctx.manifiesto["CANONICAL_RUN_INPUT_HASH"] is None
    assert ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] == 0


def test_crp_09_etapa_manifiesto_recalcula_y_vincula(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRP-09: el árbol coincidente se recalcula y vincula al hash canónico."""
    ctx = _ctx_etapa_manifiesto(tmp_path, "b" * 40)
    llamadas: list[tuple[Path, Path]] = []
    postgres_qa_temporal = tmp_path / "postgres_qa.json"
    postgres_qa_temporal.write_text("{}")
    monkeypatch.setattr(cr, "POSTGRES_QA", postgres_qa_temporal)

    def doble(ctx_interno: cr.Contexto, raiz: Path, trabajo: Path) -> dict[str, object]:
        llamadas.append((raiz, trabajo))
        return {"arbol": "b" * 40, "excluidos_con_cambios": []}

    monkeypatch.setattr(cr, "arbol_certificado", doble)
    cr.etapa_manifiesto(ctx)
    assert len(llamadas) == 1
    assert llamadas[0][0] == cr.RAIZ
    assert ctx.espacio in llamadas[0][1].parents
    assert str(ctx.manifiesto["CANONICAL_RUN_INPUT_HASH"]).startswith("sha256:")
    assert ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] == 1
    assert ctx.manifiesto["CANONICAL_RUN_INPUT_HASH_VERSION"] == 2


def test_crp_09_etapa_manifiesto_cambia_con_arbol_distinto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRP-09: árboles distintos producen hashes canónicos distintos."""
    postgres_qa_temporal = tmp_path / "postgres_qa.json"
    postgres_qa_temporal.write_text("{}")
    monkeypatch.setattr(cr, "POSTGRES_QA", postgres_qa_temporal)

    ctx_b = _ctx_etapa_manifiesto(tmp_path / "b", "b" * 40)
    monkeypatch.setattr(
        cr,
        "arbol_certificado",
        lambda ctx_interno, raiz, trabajo: {
            "arbol": "b" * 40,
            "excluidos_con_cambios": [],
        },
    )
    cr.etapa_manifiesto(ctx_b)
    hash_b = ctx_b.manifiesto["CANONICAL_RUN_INPUT_HASH"]

    ctx_c = _ctx_etapa_manifiesto(tmp_path / "c", "c" * 40)
    monkeypatch.setattr(
        cr,
        "arbol_certificado",
        lambda ctx_interno, raiz, trabajo: {
            "arbol": "c" * 40,
            "excluidos_con_cambios": [],
        },
    )
    cr.etapa_manifiesto(ctx_c)
    hash_c = ctx_c.manifiesto["CANONICAL_RUN_INPUT_HASH"]
    assert hash_b != hash_c


def test_crp_09_etapa_manifiesto_falla_si_el_arbol_cambia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRP-09: un árbol divergente al cierre interrumpe la certificación."""
    ctx = _ctx_etapa_manifiesto(tmp_path, "b" * 40)
    postgres_qa_temporal = tmp_path / "postgres_qa.json"
    postgres_qa_temporal.write_text("{}")
    monkeypatch.setattr(cr, "POSTGRES_QA", postgres_qa_temporal)
    monkeypatch.setattr(
        cr,
        "arbol_certificado",
        lambda ctx_interno, raiz, trabajo: {
            "arbol": "d" * 40,
            "excluidos_con_cambios": [],
        },
    )
    with pytest.raises(cr.FalloDeCertificacion):
        cr.etapa_manifiesto(ctx)
    assert ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] == 0


def test_crp_10_campos_y_exclusiones_del_manifiesto(tmp_path: Path) -> None:
    """CRP-10: los campos nuevos existen, inician en NOT_RUN y hay 12 exclusiones."""
    campos_nuevos = {
        "CERTIFICATION_INPUT_TREE_HASH",
        "ENVIRONMENT_POLICY",
        "POSTGRES_QA_SOURCE",
        "CANONICAL_E2E_WORKERS",
        "CANONICAL_E2E_RETRIES",
    }
    assert campos_nuevos <= set(cr.CAMPOS_DEL_MANIFIESTO)

    ctx = _contexto(tmp_path)
    for campo in campos_nuevos:
        assert ctx.manifiesto[campo] == "NOT_RUN"
    assert ctx.manifiesto["CANONICAL_RUN_INPUT_HASH_VERSION"] == 2
    assert ctx.manifiesto["TREE_HASH_BOUND_TO_RUN_INPUT"] == 0

    exclusiones_esperadas = {
        ":(exclude,glob)specs/**/evidence/**",
        ":(exclude,glob)specs/**/*.md",
        ":(exclude,glob)docs/roadmap/**",
        ":(exclude)requerimientos",
        ":(exclude,glob)**/.env",
        ":(exclude,glob)**/.env.*",
        ":(exclude,glob)**/*.pem",
        ":(exclude,glob)**/*.key",
        ":(exclude,glob)**/id_rsa*",
        ":(exclude,glob)**/id_ed25519*",
        ":(exclude,glob)**/*.p12",
        ":(exclude,glob)**/*.pfx",
    }
    assert isinstance(cr.EXCLUSIONES_DEL_ARBOL, tuple)
    assert set(cr.EXCLUSIONES_DEL_ARBOL) == exclusiones_esperadas
    assert len(cr.EXCLUSIONES_DEL_ARBOL) == 12
    assert cr.POLITICA_DE_ENTORNO_VERSION == 1
    assert cr.POLITICA_DEL_ARBOL_VERSION == 1
