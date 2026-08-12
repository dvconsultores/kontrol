#!/usr/bin/env python3
"""T-219 · Transforma router.tsx a code-splitting con `lazy` por ruta.

Lee `src/app/router.tsx`, extrae el mapa de imports de páginas y reescribe
cada ruta `{ path, element: <X/> }` a `{ path, lazy: () => import(...).then(...) }`.
Mantiene imports de componentes estáticos (ErrorBoundary, RouteGuard, AppShell,
ForbiddenState, NotFoundState).

Uso: python3 tools/code_split_router.py <router.tsx>
"""
from __future__ import annotations

import re
import sys

KEEP_IMPORTS = {"ErrorBoundary", "RouteGuard", "AppShell", "ForbiddenState", "NotFoundState"}


def build_import_map(text: str) -> dict[str, tuple[str, str]]:
    """used_name -> (module_path, exported_name)."""
    out: dict[str, tuple[str, str]] = {}
    for m in re.finditer(r'import\s*\{([^}]+)\}\s*from\s*"@/([^"]+)"', text):
        path = m.group(2)
        for name in m.group(1).split(","):
            n = name.strip()
            if not n:
                continue
            if " as " in n:
                exported, used = (x.strip() for x in n.split(" as ", 1))
                out[used] = (path, exported)
            else:
                out[n] = (path, n)
    return out


def transform(text: str, imports: dict[str, tuple[str, str]]) -> str:
    # 1) Eliminar todos los imports de páginas: `import { ... } from "@/pages...|@/modules..."`.
    lines = text.split("\n")
    kept: list[str] = []
    removed_block = False
    for ln in lines:
        m = re.match(r'import\s*\{([^}]+)\}\s*from\s*"@/(pages|modules)/', ln)
        if m:
            # conservar si algún nombre importado está en KEEP_IMPORTS (no debería ocurrir)
            names = {x.strip().split(" as ")[-1].strip() for x in m.group(1).split(",") if x.strip()}
            if not (names & KEEP_IMPORTS):
                removed_block = True
                continue
        kept.append(ln)
    text2 = "\n".join(kept)
    if removed_block:
        # limpiar líneas en blanco dobles sobrantes
        text2 = re.sub(r"\n\n\n+", "\n\n", text2)

    # 2) Reescribir rutas con element estático (solo páginas) → lazy.
    def repl(m: re.Match[str]) -> str:
        indent, path, comp, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if comp not in imports:
            # componente estático (ej. NotFoundState/ForbiddenState): no tocar
            return m.group(0)
        mod_path, exported = imports[comp]
        return (f'{indent}path: "{path}",\n'
                f'{indent}lazy: () => import("@/{mod_path}").then((m) => ({{ Component: m.{exported} }})),\n'
                f"{indent}{tail}")

    # Coincide:  { path: "X", element: <Comp /> }  (indent, path, comp, resto)
    pattern = re.compile(r'^(\s*)\{\s*path:\s*"([^"]+)"\s*,\s*element:\s*<([A-Za-z0-9_]+)\s*/>\s*(.*)$')
    out_lines = []
    for ln in text2.split("\n"):
        m = pattern.match(ln)
        out_lines.append(repl(m) if m else ln)
    return "\n".join(out_lines)


def main() -> int:
    path = sys.argv[1]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    imports = build_import_map(text)
    # Descarta componentes estáticos y NoUnused (aquellos sin ruta)
    new = transform(text, imports)
    # Conservar el resto de imports estáticos (react-router, componentes) tal cual:
    # la transformación ya los dejó; sólo aseguramos que react import no se perdió.
    if "react-router" not in new:
        print("WARN: se perdió import de react-router", file=sys.stderr)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    print(f"OK · {len(imports)} páginas en el mapa · router.tsx reescrito")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
