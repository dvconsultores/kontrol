import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { crearIndice, resolver, type Operacion } from "@/app/autoridad/operaciones";

const SRC = resolve(__dirname, "..");

const read = (rel: string): string => readFileSync(resolve(SRC, rel), "utf8");

interface InstantaneaOperaciones {
  operations: Operacion[];
  permissions: string[];
}

const instantanea = JSON.parse(
  read("tests/fixtures/operaciones.json"),
) as InstantaneaOperaciones;
const indice = crearIndice(instantanea.operations);

function recogerFuentes(): string[] {
  const resultados: string[] = [];

  const recorrer = (directorio: string): void => {
    for (const entrada of readdirSync(directorio, { withFileTypes: true })) {
      const rutaCompleta = join(directorio, entrada.name);
      if (entrada.isDirectory()) {
        recorrer(rutaCompleta);
      } else if (
        (entrada.name.endsWith(".ts") || entrada.name.endsWith(".tsx")) &&
        !entrada.name.endsWith(".test.ts") &&
        !entrada.name.endsWith(".test.tsx") &&
        !rutaCompleta.includes(`${sep}tests${sep}`)
      ) {
        resultados.push(relative(SRC, rutaCompleta));
      }
    }
  };

  recorrer(SRC);
  return resultados;
}

function llamadasMutantes(
  fuente: string,
): Array<{ metodo: string; ruta: string }> {
  const expresion =
    /apiFetch(?:<[^>]*>)?\(\s*([`"])((?:(?!\1).)+)\1\s*,\s*\{[^]{0,300}?method:\s*"(POST|PUT|PATCH|DELETE)"/g;
  const coincidencias: Array<{ metodo: string; ruta: string }> = [];
  for (const coincidencia of fuente.matchAll(expresion)) {
    coincidencias.push({ metodo: coincidencia[3], ruta: coincidencia[2] });
  }
  return coincidencias;
}

function normalizar(ruta: string): string {
  return ruta.replace(/\$\{[^}]*\}/g, "_");
}

function requierePuerta(fuente: string): boolean {
  return llamadasMutantes(fuente).some(({ metodo, ruta }) => {
    const operacion = resolver(indice, metodo, normalizar(ruta));
    return operacion === null || operacion.capabilities.length > 0;
  });
}

function tienePuerta(fuente: string): boolean {
  return /useAutoridad\(|<Autorizado[\s>]/.test(fuente);
}

const EXENTOS: Record<string, { motivo: string; uso?: RegExp }> = {
  "modules/comercial/api.ts": {
    motivo: "módulo de llamadas: la puerta va en las pantallas que lo usan",
    uso: /comercial\.(crear\w*|transicionarVersion)\(/,
  },
  "modules/gobierno/rendicion/api.ts": {
    motivo: "módulo de llamadas de CTL-05: la puerta va en las pantallas que lo usan",
    uso: /\b(crearExpediente|actualizarExpediente|incorporarPieza|retirarPieza|formarCuenta|registrarParticipacion|registrarCalificacion|registrarFenecimiento|nuevaVersion)\(/,
  },
  "api/mfa.ts": {
    motivo:
      "módulo de llamadas: el reinicio de MFA ajeno se condiciona en la pantalla de usuarios",
    uso: /resetUserMfa\(/,
  },
  "modules/notificaciones/centro/CentroNotificacionesPage.tsx": {
    motivo:
      "POST /notifications/{id}/read|archive se calcula con la acción y el catálogo no le exige capacidad",
  },
};

const fuentes = recogerFuentes();

describe("gate coverage", () => {
  it("el detector ve las llamadas mutantes del código", () => {
    const total = fuentes.reduce(
      (suma, archivo) => suma + llamadasMutantes(read(archivo)).length,
      0,
    );
    expect(total).toBeGreaterThanOrEqual(200);
  });

  it("el detector distingue los casos", () => {
    const mutanteSimple =
      'apiFetch("/sales/orders", { method: "POST", body })';
    expect(requierePuerta(mutanteSimple)).toBe(true);
    expect(tienePuerta(mutanteSimple)).toBe(false);

    const conAutorizado =
      mutanteSimple +
      '\n<Autorizado operacion={["POST", "/sales/orders"]}>';
    expect(tienePuerta(conAutorizado)).toBe(true);

    const sinCapacidad =
      'apiFetch("/auth/change-password", { method: "POST", body })';
    expect(requierePuerta(sinCapacidad)).toBe(false);

    const conPlantilla =
      'apiFetch<{ id: string }>(`/sales/orders/${id}/submit`, { method: "POST" })';
    expect(requierePuerta(conPlantilla)).toBe(true);
  });

  it("todo fichero con una acción mutante que exige autoridad tiene puerta o está exento", () => {
    const infractores = fuentes.filter((archivo) => {
      const fuente = read(archivo);
      const rutaNormalizada = archivo.split(sep).join("/");
      return (
        requierePuerta(fuente) &&
        !tienePuerta(fuente) &&
        !(rutaNormalizada in EXENTOS)
      );
    });
    expect(
      infractores,
      `Ficheros sin puerta de autoridad para acciones mutantes:\n${infractores.join("\n")}`,
    ).toEqual([]);
  });

  it("las exenciones siguen vigentes y sus consumidores llevan puerta", () => {
    for (const [rutaExenta, exencion] of Object.entries(EXENTOS)) {
      const fuenteExenta = read(rutaExenta);
      expect(
        requierePuerta(fuenteExenta),
        `La exención ${rutaExenta} ya no requiere puerta`,
      ).toBe(true);
      expect(
        tienePuerta(fuenteExenta),
        `La exención ${rutaExenta} ya tiene puerta propia`,
      ).toBe(false);

      if (!exencion.uso) continue;

      const consumidores = fuentes.filter(
        (archivo) =>
          archivo.split(sep).join("/") !== rutaExenta &&
          exencion.uso?.test(read(archivo)),
      );
      expect(
        consumidores.length,
        `La exención ${rutaExenta} no tiene consumidores vigentes`,
      ).toBeGreaterThan(0);
      for (const consumidor of consumidores) {
        expect(
          tienePuerta(read(consumidor)),
          `El consumidor ${consumidor} de la exención ${rutaExenta} no lleva puerta`,
        ).toBe(true);
      }
    }
  });

  it("las acciones del centro de notificaciones no exigen capacidad", () => {
    const lectura = resolver(indice, "POST", "/notifications/_/read");
    const archivado = resolver(indice, "POST", "/notifications/_/archive");
    expect(lectura).not.toBeNull();
    expect(archivado).not.toBeNull();
    expect(lectura?.capabilities ?? []).toEqual([]);
    expect(archivado?.capabilities ?? []).toEqual([]);
  });
});
