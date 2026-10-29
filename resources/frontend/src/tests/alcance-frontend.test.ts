import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = resolve(__dirname, "..");

function listSources(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = relative(SRC, full).split("\\").join("/");
    if (statSync(full).isDirectory()) {
      if (rel === "tests" || rel.startsWith("tests/")) continue;
      out.push(...listSources(full));
      continue;
    }
    if (!/\.(ts|tsx)$/.test(entry)) continue;
    if (/\.test\.(ts|tsx)$/.test(entry)) continue;
    out.push(full);
  }
  return out;
}

const FILES = listSources(SRC);
const SOURCES: Array<{ rel: string; content: string }> = FILES.map((full) => ({
  rel: relative(SRC, full).split("\\").join("/"),
  content: readFileSync(full, "utf8"),
}));

function offenders(check: (content: string) => boolean): string[] {
  return SOURCES.filter((s) => check(s.content)).map((s) => s.rel);
}

describe("el frontend proyecta el alcance; no lo decide (OD-ISO-05)", () => {
  it("X-Kontrol-Company solo aparece en api/client.ts", () => {
    const files = offenders((c) => c.includes("X-Kontrol-Company"));
    const unexpected = files.filter((f) => f !== "api/client.ts");
    expect(unexpected, `X-Kontrol-Company fuera de api/client.ts: ${unexpected.join(", ")}`).toEqual([]);
  });

  it("ningún fuente contiene tenant_id ni tenantId", () => {
    const files = offenders((c) => c.includes("tenant_id") || c.includes("tenantId"));
    expect(files, `tenant_id/tenantId en: ${files.join(", ")}`).toEqual([]);
  });

  it("ningún fuente compara un código de rol con un literal", () => {
    const re = /===\s*["'](ADMIN|FUNCIONAL_COMPLETO)["']/;
    const files = offenders((c) => re.test(c));
    expect(files, `comparación de rol con literal en: ${files.join(", ")}`).toEqual([]);
  });

  it("global_scope solo aparece con el literal false (OD-ISO-10)", () => {
    const re = /global_scope\s*:(?!\s*false\b)/;
    const files = offenders((c) => re.test(c));
    expect(files, `global_scope sin false en: ${files.join(", ")}`).toEqual([]);
  });
});
