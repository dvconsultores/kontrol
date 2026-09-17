/**
 * El ayudante de empresa de los E2E (Spec 054 · E2E-HELPER-EMPRESA-AMBIGUO).
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
 * Este ayudante es el único sitio donde vive esa lógica para las suites que lo
 * consumen. `approvals.spec.ts` y las de documentos ya la resolvieron en sus propios
 * ciclos y no se migran aquí: son correctas y pertenecen a deltas convergidos.
 */
import { expect, type Page } from "@playwright/test";

/** Los tres controles de la pantalla, por nombre accesible **exacto**. */
export function controlesDeEmpresa(page: Page) {
  return {
    activar: page.getByRole("button", { name: "Activar", exact: true }),
    desactivar: page.getByRole("button", { name: "Desactivar", exact: true }),
    activa: page.getByRole("button", { name: "Activa", exact: true }),
  };
}

/**
 * Deja una empresa activa y **comprueba que lo está**.
 *
 * Idempotente: si ya lo está, no pulsa nada. Si no lo está, la activa una sola vez.
 * Si el estado no es determinable, falla en el acto enumerando lo que encontró, en
 * vez de continuar a ciegas hacia un fallo que no se parece a su causa.
 *
 * `codigo` elige una empresa concreta cuando hay varias. Sin él se activa la única
 * candidata, y si hubiera más de una se exige el código en lugar de adivinar.
 */
export async function activarEmpresa(page: Page, codigo?: string): Promise<void> {
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");

  const { activar, desactivar, activa } = controlesDeEmpresa(page);

  // Regresión permanente: todo elemento que alcance el localizador de decisión se
  // llama literalmente «Activar». Si alguien retira `exact`, «Desactivar» entra en el
  // conjunto y esto falla aquí, en la causa, y no tres pantallas más abajo.
  const alcanzados = (await activar.allInnerTexts()).map((t) => t.trim());
  expect(
    alcanzados.filter((t) => t !== "Activar"),
    `el localizador de «Activar» alcanzó ${JSON.stringify(alcanzados)}`,
  ).toEqual([]);

  const yaActiva = (await desactivar.count()) > 0 && (await activa.count()) > 0;
  if (yaActiva && !codigo) return;

  // Sin empresa activa el producto retira la tabla y muestra la compuerta de
  // selección; se resuelve por el identificador canónico que el propio producto trae.
  const compuerta = codigo ? page.getByTestId(`elegir-empresa-${codigo}`) : page.getByTestId(/^elegir-empresa-/);
  const candidatas = await activar.count();
  const puerta = await compuerta.count();

  if (yaActiva && codigo) {
    // Cambio de empresa: primero se suelta la actual, que es lo que hace una persona.
    await desactivar.click();
    await expect(page.getByTestId(`elegir-empresa-${codigo}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`elegir-empresa-${codigo}`).click();
  } else {
    const diagnostico =
      `estado de empresa no determinable: activar=${candidatas} compuerta=${puerta} ` +
      `activa=${await activa.count()} desactivar=${await desactivar.count()} ` +
      `botones=${JSON.stringify((await page.getByRole("button").allInnerTexts()).map((t) => t.trim()))}`;
    expect(candidatas + puerta, diagnostico).toBe(1);
    await (puerta === 1 ? compuerta : activar).click();
  }

  // Postcondición: no basta con haber pulsado. Exactamente una empresa activa.
  await expect(desactivar).toHaveCount(1, { timeout: 15000 });
  await expect(activa).toHaveCount(1);
  await expect(activar).toHaveCount(candidatas === 0 ? 0 : candidatas - 1);
}
