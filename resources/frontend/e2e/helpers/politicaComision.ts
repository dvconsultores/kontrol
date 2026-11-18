import type { APIRequestContext } from "@playwright/test";
import { expect } from "@playwright/test";
import { API, TENANT, crearUsuario } from "./gobierno";
import { sesionApi } from "./sesion";

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

export async function politicaHistoricaE2E(
  request: APIRequestContext,
  companyId: string,
  opciones?: { maxPrincipales?: number; codigo?: string },
): Promise<string> {
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const configurador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_comisiones:view", "gobierno_comisiones:configure"],
    companyId,
  );
  const activador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_comisiones:view", "gobierno_comisiones:activate"],
    companyId,
  );

  const codigo = (opciones?.codigo ?? `PH${Date.now().toString(36).toUpperCase()}`).slice(0, 20);
  const crearResp = await request.post(`${API}/gobierno/contrataciones/politicas-comision`, {
    headers: configurador.headers,
    data: {
      codigo,
      nombre: "Política histórica E2E",
      tipo_comision: "CUALQUIERA",
      base_normativa: "LCP_ART14",
      fundamento: "Ley de Contrataciones Públicas, art. 14",
      vigente_desde: hoyCaracas(),
      min_principales: 1,
      max_principales: opciones?.maxPrincipales ?? null,
      exige_impar: true,
      suplente_por_principal: true,
      exige_secretario: true,
      exige_suplente_secretario: true,
      exige_presidente: false,
      quorum: { tipo: "SIMPLE_MAJORITY" },
      decision: { tipo: "SIMPLE_MAJORITY", base: "MIEMBROS_CON_VOTO" },
      requisitos: [],
      documentos: [],
    },
  });
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  const creada = await crearResp.json();
  const id = creada.id as string;
  const version = creada.version as number;

  const activarResp = await request.post(
    `${API}/gobierno/contrataciones/politicas-comision/${id}/activar`,
    {
      headers: { ...activador.headers, "If-Match": String(version) },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return id;
}
