# CTL-03 · Matriz de superficies que crean o amplían autoridad (medida en `d1d0a0a`)

Inventario por lectura del código (`app/`), las migraciones y los routers. «ADMIN puro» = cuenta con el rol protegido ADMIN y
sin FUNCIONAL_COMPLETO ni otro rol con capacidades fuera de `TECHNICAL_CAPABILITIES` (`identity_access/authority.py`).

## A. Plataforma (identity_access y setup)

| Superficie | Permiso técnico / funcional | Qué autoridad puede crear | Control vigente (backend) | Auditoría | ¿ADMIN puro la usa? | Resultado esperado |
|---|---|---|---|---|---|---|
| `POST /users/{id}/roles` | `roles:edit` (técnico) + reautenticación | Cualquier rol, incluido FUNCIONAL_COMPLETO | `check_can_assign`: capacidades del rol ⊆ las del actor; rol protegido solo si el actor lo tiene en ese alcance; alcance por capacidad; bloqueo `lock_tenant_authority` | ROLE_ASSIGNED; AUTHORITY_DELEGATION_DENIED (SELF_ESCALATION_FORBIDDEN, AUTHORITY_CEILING_EXCEEDED, CROSS_SCOPE_DELEGATION_FORBIDDEN) | Sí, solo roles cuyas capacidades tiene | Asignarse o asignar FUNCIONAL_COMPLETO o un rol funcional: 403 y evento de denegación |
| `DELETE /users/{id}/roles/{role_id}` | `roles:edit` | Ninguna (retira) | `check_can_manage_assignment`; último administrador de seguridad | ROLE_REMOVED; LAST_ADMIN_OPERATION_DENIED | Sí, sobre roles a su alcance | No amplía autoridad |
| `POST /roles` | `roles:create` (técnico) | Un rol nuevo con capacidades | `check_can_create_role`: capacidades ⊆ las del actor, en todo el alcance pedido; bloqueo por tenant | ROLE_CREATED; AUTHORITY_DELEGATION_DENIED | Sí, solo con capacidades técnicas | Rol sombra con capacidad funcional: 403, sin persistir. «ADMIN2», «ROOT»: el nombre no da nada; decide el conjunto de capacidades |
| Edición de permisos de un rol | — | — | No existe endpoint | — | No | Sin superficie |
| `POST /users` | `users:create` | Ninguna: no lleva roles ni ámbitos | Cuerpo sin roles | USER_CREATED | Sí (tarea técnica legítima) | Crea la cuenta sin autoridad |
| Ámbitos de empresa (`UserScope`) | — | Ampliaría el alcance de roles globales | No hay escritura en `app/` | — | No | Sin superficie |
| Instalación (`/setup/initialize`) | Sin sesión, una vez | ADMIN y FUNCIONAL_COMPLETO al usuario inicial | `_bootstrap_roles`: ADMIN = exactamente las capacidades técnicas; FUNCIONAL_COMPLETO = el resto; idempotente; SETUP_ALREADY_DONE | ROLE_ASSIGNED con `source=SETUP` (dos concesiones separadas) | No (instalación ya hecha) | Concesión explícita y visible; no es violación |
| Migraciones 0063–0096 | — | Capacidades nuevas | Todas conceden **solo** a FUNCIONAL_COMPLETO; ninguna posterior a 0060 concede a ADMIN | — | — | ADMIN no recibe capacidades de negocio por migración |
| `users:mfa_reset` | técnico | Ninguna | Reautenticación; `mfa_service.admin_reset` | La del servicio MFA | Sí | No concede autoridad |
| Contexto de empresa | — | Ejercer una capacidad en otra empresa | `get_company_context` exige la capacidad del endpoint en la empresa activa (`require_capability_in_company`) | COMPANY_SCOPE_DENIED | — | Fuera de alcance: 403 |

## B. Gobierno (autoridad institucional)

| Superficie | Permiso | Qué autoridad puede crear | Control vigente | ¿ADMIN puro la usa? | Resultado esperado |
|---|---|---|---|---|---|
| ORG-03 cargos y competencias | `gobierno_cargos:edit/publish` (funcional) | Competencias acción × materia y límites | Permiso funcional; versión; publicación | No | 403 |
| ORG-04 ocupaciones (titularidad, encargaduría, suplencia, comisión, delegación) | `gobierno_ocupacion:manage/activate/revoke` (funcional; activar con MFA) | Ejercer un cargo | Permiso funcional; maker-checker (GOV_ASSIGNMENT_SELF_ACTIVATION); nadie registra ni activa la ocupación de su propio funcionario (GOV_ASSIGNMENT_SELF_AUTHORITY); acto | No | 403; con permiso, autoocupación 409/422 |
| ORG-06 vínculo cuenta ↔ funcionario | `gobierno_identidad:manage/activate/revoke` (funcional) | Identidad institucional | Permiso funcional; GOV_IDENTITY_SELF_LINK; GOV_IDENTITY_SELF_ACTIVATION; actor efectivo | No | 403 |
| ORG-06 categorías de rol | `gobierno_identidad:*` | Metadato SoD (no concede) | Permiso funcional | No | 403 |
| ORG-06 política de exigencia de identidad | `gobierno_identidad:activate` + MFA | Activa o desactiva la guarda de cargo | Permiso funcional; If-Match; historia; GOV_IDENTITY_POLICY_CHANGED | No | 403 |
| ORG-07 matriz de autoridad | `gobierno_autoridad:view` | Ninguna (proyección) | Sin mutaciones | — | — |
| CTL-01 reglas SoD | `gobierno_sod:manage/activate` | Incompatibilidades (no concede) | Permiso funcional; activar con MFA | No | 403 |
| DOC-02 emitir acto | `gobierno_actos:issue` | Ejercicio de competencia | Permiso funcional + `exigir_autoridad_funcional` (si la exigencia está activa: vínculo, ocupación que ejerce el cargo del acto, competencia acción × materia, SoD) | No | 403; dual sin identidad con exigencia activa: GOV_IDENTITY_LINK_REQUIRED |
| PROC-08 decisión, PROC-10 liberar/ejecutar | `gobierno_decision:decide`, `gobierno_garantias:release/execute` | Actos de negocio | Permiso funcional + acto DOC-02 competente + `exigir_autoridad_funcional` | No | 403 |
| Aprobaciones (Spec 045) | `aprobaciones:configure` / `aprobaciones:approve` (funcional) | Quién aprueba | Permiso funcional + actor elegible del paso; delegación de aprobación con su propio control | No | 403 aunque una regla lo nombrara |

## C. Conclusión

`CTL03_AUTHORITY_SURFACE_INVENTORY_COMPLETE = 1`. **No se halló ninguna superficie que conceda autoridad funcional a un ADMIN
puro**: ADMIN solo tiene capacidades técnicas (instalación y migraciones), toda superficie de Gobierno exige una capacidad
funcional, y la concesión de roles y la creación de roles respetan el techo con bloqueo por tenant. No se escribe código en las
autoridades propietarias (escenario A).

Hallazgos declarados (no son fabricación por ADMIN):
- OD-ORG06-09: con la exigencia de identidad **inactiva** (por defecto), `exigir_autoridad_funcional` no comprueba el cargo
  del usuario; basta el permiso funcional y el acto competente. Es una decisión vigente; la pantalla de CTL-03 lo muestra.
- Las denegaciones de autoridad propia de ORG-04 y ORG-06 se rechazan sin evento de auditoría propio; las de identity_access
  y la guarda de identidad sí dejan evento.
