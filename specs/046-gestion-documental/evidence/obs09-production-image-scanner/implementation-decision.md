# Gate material y decisión sobre el runtime de contenedores
| Pregunta | Respuesta |
|---|---|
| `ROOT_CAUSE_PROVEN` | 1 (`root-cause.md`) |
| ¿Cambio de política funcional? | NO: el máximo documental (50 MiB) no cambia; el servicio se configura para soportarlo (`size-contract.md`) |
| ¿Cambio de producto? | SÍ, el autorizado: adaptador `ClamdScanner` + 3 campos de `Settings`; API, esquema, migraciones, falso seguro y semántica CLEAN/INFECTED/SCAN_FAILED sin cambio |
| ¿Runtime de contenedores en el equipo de QA? | **NO** (`docker`, `podman`, `nerdctl` ausentes; sin `sudo`). Las medidas que lo exigen (`docker build`, tamaño de imagen, `compose up`, healthcheck real, `inspect`) no pueden hacerse aquí |
| Qué se demuestra sin runtime | el contrato completo del adaptador contra el **demonio real** 1.4.3 (mismo paquete y misma versión que la imagen oficial, misma `clamd.conf` adaptada): CLEAN, EICAR, varios trozos, 50 MiB, límite del demonio, caído, timeout, protocolo, truncada, flujo cortado, sin rutas; y el contrato estático de imagen y composición (sin puerto publicado, sin almacén, backend sin firmas, límites ≥ 50 MiB, selección explícita, healthcheck PING) |
| Qué queda pendiente | ejecutar en un equipo con Docker los pasos de `docs/evidence/docker-validation-checklist.md` (sección OBS-09) y registrar `compose-runtime-evidence.md`; hasta entonces `CLAMD_SERVICE_PRESENT` y el contrato se certifican **estáticamente** y el demonio **localmente** |
| Verdicto previsible | OBS-09 **no** puede declararse `CLOSED / CONVERGED` sin esa evidencia de composición: queda `IMPLEMENTATION IN PROGRESS — BLOCKED BY ENVIRONMENT (COMPOSE_RUNTIME_UNAVAILABLE)` con todo lo demás convergido (ver `convergence.md`) |
`MATERIAL OQ = 0` (ninguna decisión de negocio o arquitectura abierta: B está ratificada y aplicada); `UNKNOWN = 0`.
