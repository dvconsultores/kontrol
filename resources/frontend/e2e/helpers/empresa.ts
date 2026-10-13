/**
 * El ayudante de empresa de los E2E (Spec 054 · E2E-HELPER-EMPRESA-AMBIGUO y
 * E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO).
 *
 * `EmpresasPage` pinta, por fila, controles **mutuamente excluyentes**: la empresa
 * activa muestra «Activa» (deshabilitado) y «Desactivar»; cualquier otra muestra
 * «Activar». Los tres nombres accesibles son exactos y distintos, así que el producto
 * no tiene ambigüedad ninguna.
 *
 * La ponían las pruebas. `getByRole("button", { name: "Activar" })` casa **por
 * subcadena** con «Des**activar**»: con la empresa ya activa, el ayudante pulsaba el
 * control contrario —desactivando la empresa que necesitaba— y acto seguido esperaba
 * ver el botón que él mismo acababa de hacer desaparecer. De ahí salían doce fallos
 * repartidos en cuatro ficheros, y una suite E2E cuya señal no se podía leer.
 *
 * La segunda vez la ponía el tiempo. El ayudante decidía con `count()` instantáneos
 * tras `networkidle`, que solo ve peticiones ya emitidas: bajo carga, la página pedía
 * la tabla ≈360 ms después del cambio de ruta, `networkidle` ya se había resuelto y los
 * conteos se hacían sobre una pantalla sin pintar («estado de empresa no determinable»
 * con todo a cero; milisegundos después, pintada). Ahora el ayudante espera, con la
 * auto-repetición de Playwright, a que la pantalla muestre uno y solo uno de sus estados
 * válidos, y decide con esa misma lectura.
 *
 * Este ayudante es el único sitio donde vive esa lógica para las suites que lo
 * consumen. `approvals.spec.ts` conserva su propia compuerta por código de empresa y
 * comparte de aquí la espera; las de documentos pulsan «Activar» solo si lo ven y
 * pertenecen a deltas convergidos.
 */
import { expect, type Locator, type Page } from "@playwright/test";

/** Los tres controles de la pantalla, por nombre accesible **exacto**. */
export function controlesDeEmpresa(page: Page) {
  return {
    activar: page.getByRole("button", { name: "Activar", exact: true }),
    desactivar: page.getByRole("button", { name: "Desactivar", exact: true }),
    activa: page.getByRole("button", { name: "Activa", exact: true }),
  };
}

/** Lo que la pantalla de empresas puede estar mostrando, leído de sus controles exactos. */
export type EstadoDeEmpresa = "ACTIVA" | "INACTIVA" | "COMPUERTA" | "NO_LISTA" | "AMBIGUO";

/** Una lectura de la pantalla: el estado y los conteos con que se clasificó. */
export interface LecturaDeEmpresa {
  estado: EstadoDeEmpresa;
  activar: number;
  desactivar: number;
  activa: number;
  compuerta: number;
  cargando: number;
  botones: string[];
}

/** El tiempo que el ayudante concede a sus esperas; el mismo de siempre. */
export const ESPERA_DEL_AYUDANTE_MS = 15000;

/**
 * Una fotografía instantánea de la pantalla, clasificada. No decide nada por sí sola.
 *
 * La pareja «Activa» + «Desactivar» es UN estado (ACTIVA). Todo a cero es NO_LISTA:
 * cargando o sin pintar, legítimo mientras no se agote el tiempo. Cualquier otra
 * combinación es AMBIGUO.
 */
export async function leerEstadoDeEmpresa(page: Page, compuerta: Locator): Promise<LecturaDeEmpresa> {
  const { activar, desactivar, activa } = controlesDeEmpresa(page);
  const [nActivar, nDesactivar, nActiva, nCompuerta, cargando, botones] = await Promise.all([
    activar.count(),
    desactivar.count(),
    activa.count(),
    compuerta.count(),
    page.getByRole("status").count(),
    page.getByRole("button").allInnerTexts(),
  ]);
  let estado: EstadoDeEmpresa;
  if (nDesactivar === 1 && nActiva === 1 && nCompuerta === 0) estado = "ACTIVA";
  else if (nDesactivar === 0 && nActiva === 0 && nCompuerta === 0 && nActivar >= 1) estado = "INACTIVA";
  else if (nDesactivar === 0 && nActiva === 0 && nActivar === 0 && nCompuerta >= 1) estado = "COMPUERTA";
  else if (nDesactivar === 0 && nActiva === 0 && nActivar === 0 && nCompuerta === 0) estado = "NO_LISTA";
  else estado = "AMBIGUO";
  return {
    estado,
    activar: nActivar,
    desactivar: nDesactivar,
    activa: nActiva,
    compuerta: nCompuerta,
    cargando,
    botones: botones.map((t) => t.trim()),
  };
}

/** El diagnóstico que acompaña a todo fallo del ayudante: lo que encontró, enumerado. */
export function diagnosticoDeEmpresa(lectura: LecturaDeEmpresa): string {
  return (
    `activar=${lectura.activar} compuerta=${lectura.compuerta} activa=${lectura.activa} ` +
    `desactivar=${lectura.desactivar} cargando=${lectura.cargando} botones=${JSON.stringify(lectura.botones)}`
  );
}

/**
 * Espera a que la pantalla muestre uno —y solo uno— de los estados válidos y devuelve
 * esa lectura, que es la que debe usarse para decidir: no se vuelve a leer después.
 *
 * Mientras no haya nada pintado (NO_LISTA) o la lectura sea contradictoria (AMBIGUO),
 * sigue intentándolo hasta agotar el tiempo de siempre; entonces falla con el último
 * diagnóstico. Ni `networkidle` ni esperas fijas: lo que manda es lo que se ve.
 */
export async function esperarEstadoDeEmpresa(
  page: Page,
  compuerta: Locator,
  timeout: number = ESPERA_DEL_AYUDANTE_MS,
): Promise<LecturaDeEmpresa> {
  let lectura: LecturaDeEmpresa | undefined;
  await expect
    .poll(
      async () => {
        lectura = await leerEstadoDeEmpresa(page, compuerta);
        return lectura.estado === "ACTIVA" || lectura.estado === "INACTIVA" || lectura.estado === "COMPUERTA"
          ? lectura.estado
          : `${lectura.estado}: ${diagnosticoDeEmpresa(lectura)}`;
      },
      { timeout, message: "estado de empresa no determinable" },
    )
    .toMatch(/^(ACTIVA|INACTIVA|COMPUERTA)$/);
  return lectura as LecturaDeEmpresa;
}

/**
 * Sonda de arnés (solo pruebas del ayudante): difiere, dentro de la propia página, la
 * EMISIÓN de la petición del listado de la tabla de empresas `despuesDeMs` milisegundos
 * (`null`: no la emite nunca). Reproduce a voluntad la carrera de pintado: con la
 * petición sin emitir, `networkidle` se resuelve en 500 ms y una decisión instantánea
 * cuenta sobre una pantalla vacía. Retrasar la RESPUESTA con `page.route` no la
 * reproduce, porque una petición en vuelo mantiene `networkidle` esperando. Se instala
 * antes de cargar la aplicación; no toca producto ni red.
 */
export async function emitirLaTablaTarde(page: Page, despuesDeMs: number | null): Promise<void> {
  await page.addInitScript((retraso: number | null) => {
    const original = window.fetch.bind(window);
    window.fetch = async (entrada: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
      if (/\/organization\/companies\?page=1&page_size=10\b/.test(url)) {
        if (retraso === null) await new Promise<never>(() => undefined);
        else await new Promise<void>((listo) => setTimeout(listo, retraso));
      }
      return original(entrada, init);
    };
  }, despuesDeMs);
}

/**
 * Deja una empresa activa y **comprueba que lo está**.
 *
 * Idempotente: si ya lo está, no pulsa nada. Si no lo está, la activa una sola vez.
 * Si el estado no es determinable en el tiempo de siempre, falla enumerando lo que
 * encontró, en vez de continuar a ciegas hacia un fallo que no se parece a su causa.
 *
 * `codigo` elige una empresa concreta cuando hay varias. Sin él se activa la única
 * candidata, y si hubiera más de una se exige el código en lugar de adivinar.
 */
export async function activarEmpresa(page: Page, codigo?: string): Promise<void> {
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });

  const { activar, desactivar, activa } = controlesDeEmpresa(page);
  // Sin empresa activa el producto retira la tabla y muestra la compuerta de
  // selección; se resuelve por el identificador canónico que el propio producto trae.
  const compuerta = codigo ? page.getByTestId(`elegir-empresa-${codigo}`) : page.getByTestId(/^elegir-empresa-/);

  // La decisión se toma sobre la lectura que ya es determinable, y solo sobre ella.
  const lectura = await esperarEstadoDeEmpresa(page, compuerta);

  // Regresión permanente: todo elemento que alcance el localizador de decisión se
  // llama literalmente «Activar». Si alguien retira `exact`, «Desactivar» entra en el
  // conjunto y esto falla aquí, en la causa, y no tres pantallas más abajo.
  const alcanzados = (await activar.allInnerTexts()).map((t) => t.trim());
  expect(
    alcanzados.filter((t) => t !== "Activar"),
    `el localizador de «Activar» alcanzó ${JSON.stringify(alcanzados)}`,
  ).toEqual([]);

  if (lectura.estado === "ACTIVA" && !codigo) return;

  const candidatas = lectura.activar;
  if (lectura.estado === "ACTIVA") {
    // Cambio de empresa: primero se suelta la actual, que es lo que hace una persona.
    await desactivar.click();
    await expect(page.getByTestId(`elegir-empresa-${codigo}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`elegir-empresa-${codigo}`).click();
  } else {
    expect(candidatas + lectura.compuerta, `estado de empresa no determinable: ${diagnosticoDeEmpresa(lectura)}`).toBe(1);
    await (lectura.estado === "COMPUERTA" ? compuerta : activar).click();
  }

  // Postcondición: no basta con haber pulsado. Exactamente una empresa activa.
  await expect(desactivar).toHaveCount(1, { timeout: 15000 });
  await expect(activa).toHaveCount(1);
  await expect(activar).toHaveCount(candidatas === 0 ? 0 : candidatas - 1);
}
