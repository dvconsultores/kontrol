/**
 * Siembra la base antes de la suite.
 *
 * Las suites de N6 necesitan un mundo —dos empresas del mismo tenant, un tenant
 * ajeno y los usuarios `ua`/`ub`/`uab`— que ningún paso automático escribía: su
 * único guion fabricaba una base SQLite propia, así que contra la base del E2E
 * esos usuarios no existían y 25 pruebas se quedaban en el formulario de acceso
 * hasta agotar el tiempo. Veinticinco caducidades de veinte segundos no dicen
 * qué falta; esto lo deja escrito antes de empezar.
 *
 * Solo actúa cuando el lanzador declara contra qué base corre. Sin
 * `KONTROL_E2E_DB_URL` no se toca nada: quien apunta la suite a una pila que no
 * administra —remota, compartida, ya sembrada— no quiere que nadie le escriba
 * en ella.
 *
 * Y cuando sí la declara, si la siembra no puede ejecutarse **esto falla**. Un
 * aviso por consola se pierde entre doscientas líneas de resultados y el
 * síntoma reaparecería igual de mudo que antes.
 */
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export default function sembrar(): void {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) return;
  // Una corrida lanzada por `qa/e2e-run.py` trae su propia base, recién creada y ya
  // sembrada una vez: sembrarla de nuevo aquí sería la segunda siembra de una base que
  // solo debe tener una.
  if (process.env.KONTROL_E2E_RUN_ID) return;

  const guion = fileURLToPath(new URL("../../../qa/e2e-seed.sh", import.meta.url));
  execFileSync("bash", [guion, url], { stdio: "inherit" });
}
