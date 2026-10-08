# Runbook — rotación de la clave de firma del propietario (A → B) con solapamiento

Dominio: **claves de firma de licencias del propietario** (no las claves de identidad de las
instalaciones, que autentican el sync y no se rotan aquí). Sin KMS obligatorio: las claves llegan por
configuración externa; la privada vive solo en la infraestructura del propietario. `kid` identifica
la clave; no ordena nada. El criterio de retiro lo fija el operador cuando la flota objetivo tiene la
confianza nueva y, donde haga falta, su licencia firmada con B; no hay plazo fijo.

| Fase | Autoridad Central | Clientes | Comprobación |
|---|---|---|---|
| **R0** actual | `SIGNING_PRIVATE_KEY_PEM` = A, `SIGNING_KID` = `kid-A` | `LICENSE_PUBLIC_KEY_PEM` = pubA, `LICENSE_PUBLIC_KEY_KID` = `kid-A` | las emisiones llevan `kid-A` y verifican |
| **R1** pre-stage | R1. Generar B fuera de la autoridad (Ed25519, PKCS8); nunca en producción desde el servicio. Derivar pubB | R2–R3. Desplegar `LICENSE_TRUST_KEYS = {"kid-A": pubA, "kid-B": pubB}` (reinicio del backend) | R4. Una licencia A sigue entrando; R5. una sintética firmada con B y `kid-B` entra en QA |
| **R2** activar | R6. `SIGNING_KEYS = {"kid-A": A, "kid-B": B}` y `SIGNING_KID = kid-B` (reinicio). Si `kid-B` no tiene clave, la autoridad **no arranca** | — | las emisiones nuevas llevan `kid-B` y su firma verifica con pubB |
| **R3** migrar | R7. Reemitir las licencias necesarias bajo B: cada reemisión recibe una `revision` nueva del linaje; el libro conserva las filas A | R8. Los clientes sincronizan o importan las B-firmadas; período y `revision` siguen mandando (una A anterior no pisa una B posterior) | `/license/detail` muestra `kid-B` |
| **R4** retirar A | Opcional: quitar A de `SIGNING_KEYS` | R9. `LICENSE_TRUST_KEYS = {"kid-B": pubB}` y retirar el par `LICENSE_PUBLIC_KEY_PEM`/`_KID` o apuntarlo a B (reinicio) | R10. Una importación nueva con `kid-A` responde 423 `LICENSE_SIGNING_KID_UNKNOWN` |

Reglas que el runbook no puede saltarse: el conjunto de confianza nunca se actualiza por sync, por
respuesta de la autoridad ni por el `kid` de un paquete; un `kid` con dos claves distintas o una clave
bajo dos `kid` impide arrancar; el estado ya persistido **no** se revalida al retirar A en este ciclo
(`LICENCIA-ESTADO-SIN-REVERIFICAR`, abierta); nunca se reescribe ni se vuelve a firmar el historial.
