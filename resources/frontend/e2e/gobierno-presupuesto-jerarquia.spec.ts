import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  cerrarNotificaciones,
  entrarEnGobierno,
  prepararMundo,
} from "./helpers/gobierno";
import type { Page } from "@playwright/test";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page })
    .include("main")
    .withTags(WCAG)
    .analyze();

  const serias = resultados.violations.filter((v) =>
    ["critical", "serious"].includes(v.impact ?? ""),
  );

  expect(
    serias.map((v) => ({ id: v.id, help: v.help })),
    contexto,
  ).toEqual([]);

  if (page.viewportSize()?.width === 320) {
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento, contexto).toBe(true);
  }
}

test.describe("Jerarquía del clasificador presupuestario", () => {
  test("BUD-02: el padre debe ser del nivel inmediatamente anterior (alta y CSV)", async ({ page, request }) => {
    test.setTimeout(300_000);

    const CAPACIDADES = [
      "organization:view",
      "gobierno_presupuesto:view",
      "gobierno_presupuesto:manage",
    ];
    const anio = ANIO + 3;

    const mundo = await prepararMundo(request, CAPACIDADES);

    const crearEjercicioResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios`,
      {
        headers: mundo.headers,
        data: { anio },
      },
    );
    expect(crearEjercicioResp.status(), await crearEjercicioResp.text()).toBe(201);
    const ejercicio = await crearEjercicioResp.json();
    const id = ejercicio.id as string;
    const version = ejercicio.version as number;

    const registrarClasificadorResp = await request.put(
      `${API}/gobierno/presupuesto/ejercicios/${id}/clasificador`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          edicion: "Clasificador del ente",
          procedencia: "Edición cargada para la prueba de jerarquía",
        },
      },
    );
    expect(registrarClasificadorResp.status(), await registrarClasificadorResp.text()).toBe(200);

    await entrarEnGobierno(
      page,
      mundo.username,
      mundo.codigo,
      "/gobierno/presupuesto/ejercicios",
    );
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: `Ejercicio ${anio}`, exact: true }).click();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: `Ejercicio presupuestario ${anio}`,
        exact: true,
      }),
    ).toBeVisible();

    const seccionClasificador = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Clasificador registrado por el ente" }),
    });
    const regionPartidas = page.getByRole("region", { name: "Partidas del clasificador" });
    const formAlta = seccionClasificador.locator("form").filter({
      has: page.getByRole("heading", { name: "Nueva partida" }),
    });
    const formImportar = seccionClasificador.locator("form").filter({
      has: page.getByRole("heading", { name: "Importar partidas (CSV)" }),
    });

    async function agregarPartida(codigo: string, nivel: number, superior: string) {
      await formAlta.getByLabel("Tipo", { exact: true }).selectOption("EGRESO");
      await formAlta.getByLabel("Código", { exact: true }).fill(codigo);
      await formAlta.getByLabel("Denominación", { exact: true }).fill(`Partida ${codigo}`);
      await formAlta.getByLabel("Nivel", { exact: true }).fill(String(nivel));
      if (superior !== "") {
        await formAlta.getByLabel("Código superior", { exact: true }).fill(superior);
      }

      const [resp] = await Promise.all([
        page.waitForResponse(
          (r) =>
            r.request().method() === "POST" &&
            new URL(r.url()).pathname.endsWith(
              `/gobierno/presupuesto/ejercicios/${id}/clasificador/partidas`,
            ),
          { timeout: 60_000 },
        ),
        formAlta.getByRole("button", { name: "Agregar partida" }).click(),
      ]);

      return resp;
    }

    const resp501 = await agregarPartida("501", 1, "");
    expect(resp501.status(), await resp501.text()).toBe(201);

    const resp50101 = await agregarPartida("501.01", 2, "501");
    expect(resp50101.status(), await resp50101.text()).toBe(201);

    const resp5010101 = await agregarPartida("501.01.01", 3, "501.01");
    expect(resp5010101.status(), await resp5010101.text()).toBe(201);

    const respInvalido = await agregarPartida("501.01.02", 3, "501");
    expect(respInvalido.status(), await respInvalido.text()).toBe(422);

    await expect(formAlta.getByRole("alert")).toContainText(
      "La partida padre «501» es de nivel 1; una partida de nivel 3 necesita un padre de nivel 2",
    );
    await expect(regionPartidas).not.toContainText("501.01.02");

    const respCorregido = await agregarPartida("501.01.02", 3, "501.01");
    expect(respCorregido.status(), await respCorregido.text()).toBe(201);
    await expect(regionPartidas).toContainText("501.01.02");

    const csvInvalido = [
      "tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta",
      "EGRESO,502,Partida 502,1,,,",
      "EGRESO,502.01,Partida 502.01,2,502,,",
      "EGRESO,502.01.01,Partida 502.01.01,3,502,,",
    ].join("\n");

    await formImportar
      .getByLabel("Archivo CSV de partidas")
      .setInputFiles({ name: "partidas.csv", mimeType: "text/csv", buffer: Buffer.from(csvInvalido) });

    const [respImportar] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(
            `/gobierno/presupuesto/ejercicios/${id}/clasificador/importar`,
          ),
        { timeout: 60_000 },
      ),
      formImportar.getByRole("button", { name: "Importar partidas" }).click(),
    ]);
    expect(respImportar.status(), await respImportar.text()).toBe(422);

    await expect(formImportar.getByRole("alert")).toContainText(
      "Fila 4: La partida padre «502» es de nivel 1",
    );
    await expect(regionPartidas).not.toContainText("502");

    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await sinViolacionesSerias(page, `BUD-02 jerarquía ${width}px`);
    }
  });
});
