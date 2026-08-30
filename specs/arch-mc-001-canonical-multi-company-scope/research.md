# INVESTIGACIÓN — ARCH-MC-001

## 1. Transporte del contexto de empresa

Cuatro modelos comparados sobre criterios que importan aquí, no en abstracto.

| Criterio | A · Cabecera | B · Sesión servidor | C · Claim del token | D · Ruta |
|---|---|---|---|---|
| Sin estado | ✅ | ❌ | ✅ | ✅ |
| Cambiar de empresa | inmediato | requiere escribir sesión | **exige renovar token** | navegar |
| **Dos pestañas en empresas distintas** | ✅ natural | ❌ **una selección global las contamina** | ❌ el token es del navegador | ✅ |
| Compatible con la rotación de `/auth/refresh` | ✅ no la toca | ⚠️ | ❌ **acopla empresa y sesión** | ✅ |
| Auditable | ✅ va en cada petición | ⚠️ implícito | ✅ | ✅ |
| Coste de adopción | 1 interceptor + 1 dependencia | media | alto | **294 rutas** |
| APIs externas | ✅ explícito | ❌ | ⚠️ | ✅ |

### Elección: **A · cabecera explícita por petición**

`X-Kontrol-Company` en cada petición de alcance de empresa, validada en el
servidor contra los accesos del usuario.

Las razones, en orden:

1. **Dos pestañas.** El §18 del encargo lo exige. Con sesión en servidor o claim
   en el token, elegir la empresa B en una pestaña haría que una acción lanzada
   desde la pestaña A terminase en B. Es un fallo silencioso y con consecuencias
   fiscales. Con cabecera, cada petición dice en qué empresa ocurre.
2. **No toca la autenticación.** `REM-AUTH-ROUTE-CRAWL-001` cerró una carrera en
   la renovación. Meter la empresa en el token obligaría a renovar al cambiar de
   empresa y reabriría exactamente ese terreno.
3. **Auditable por construcción.** La empresa viaja con la operación.

Descartadas: **B** por las pestañas y por introducir estado; **C** por acoplar
empresa y sesión; **D** porque reescribiría 294 rutas sin resolver nada que la
cabecera no resuelva.

> La cabecera es una **propuesta** del cliente. La autoridad es el servidor, que
> resuelve `CompanyContext` solo tras validar. Sin cabecera y con una sola empresa
> autorizada, se resuelve sola (`FR-MC-013`); sin cabecera y con varias, la
> operación de empresa se rechaza: adivinar sería peor.

## 2. Propiedad: columna directa frente a derivación

| Enfoque | A favor | En contra |
|---|---|---|
| `company_id` en todas | Consulta trivial, un solo índice | 36 columnas redundantes que pueden **contradecir** a su padre |
| Derivación donde hay padre obligatorio | Una sola verdad; imposible contradecir | Un `join` más |

### Elección: **híbrida, decidida entidad por entidad**

- **Directa** cuando la entidad es cabecera o maestro: 97 tablas.
- **Derivada** cuando existe FK **obligatoria** a una autoridad de empresa: 36.

Medido: las 36 derivan por FK **no anulable**. Ninguna necesita la segunda pasada
que admitía FK anulable. Eso hace la derivación segura: no hay ruta que pueda
desaparecer.

Duplicar `company_id` en una línea cuya cabecera ya lo tiene crea la posibilidad
de que difieran. Un `join` es más barato que una contradicción.

## 3. Estrategia de migración

| Estrategia | Veredicto |
|---|---|
| En sitio, una migración | **Descartada.** 82 tablas, sin vuelta atrás, con datos fiscales |
| Doble lectura/escritura indefinida | **Descartada.** Deuda dual permanente, prohibida por el §103 |
| **Expandir → rellenar → verificar → conmutar → restringir → contraer** | **Elegida** |
| Por olas de dominio | **Elegida como eje**, dentro del patrón anterior |

Las dos elegidas se combinan: el patrón da la seguridad; las olas, el orden.

**Orden derivado de las FK reales, no impuesto:** organización y contexto →
maestros → fiscal → compras → inventario → ventas → CxC/CxP → tesorería →
regulatorio → consumidores transversales.

Regla dura: **ninguna hija se migra antes que su cabecera** (§106).

## 4. Lecciones de las Specs cerradas

| Spec | Lección | Aplicación |
|---|---|---|
| **008** | Usó FK real a `companies` desde el principio | Es la referencia positiva; las 17 correctas son suyas y de 045/046 |
| **011** | «El dato no se pierde: nunca se captura» | La ventana de backfill determinista se cierra sola |
| **011** | `Float` en magnitudes salió caro | Aquí el equivalente es la columna que miente sobre lo que guarda |
| **046** | Anotar ≠ convertir | Una fila sin empresa reconstruible se anota, no se adivina |
| **046** | Registro cerrado mejor que inferir del nombre | `ResourceKind` declarará su alcance explícitamente |
| **045** | Una sola autoridad transversal | El `CompanyContext` es una, no una por módulo |

## 5. Por qué el apaño de `ResourceKind` no basta

Se consideró que `ResourceKind` declarase si su columna guarda empresa o tenant.
Haría funcionar la Spec 046 en pocas líneas.

Se descarta: haría funcionar el registro documental **sobre una arquitectura que
sigue sin distinguir empresas**. Los libros fiscales seguirían mezclados y la
Spec 012 añadiría nueve tablas más al defecto. Es «funciona por ahora», que este
Gate excluye por escrito.

`ResourceKind` **sí** declarará su alcance (`FR-MC-072`), pero como defensa
arquitectónica **después** de normalizar, no en lugar de hacerlo.
