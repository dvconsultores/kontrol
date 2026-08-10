# Spec 012 — Validaciones Pendientes (T-12..T-16)

Estas validaciones **no se ejecutaron** porque requieren ambiente autorizado,
dispositivos/navegadores reales o infraestructura que no está disponible en esta
sesión. No se afirma su resultado.

## T-12 · Navegadores reales + responsive + accesibilidad
- Probar Chrome, Edge, Firefox (desktop) y Chrome Android, Safari iOS/iPadOS,
  Samsung Internet (dispositivo real o servicio BrowserStack/Sauce/LambdaTest).
- Estado actual: solo `SIMULATED_ENGINE_VALIDATION` (Chromium/WebKit/Firefox headless).
- Viewports 320×568 → 1920×1080; zoom 110/125/150/200 %; sin scroll horizontal.
- Accesibilidad: ejecutar axe (WCAG 2.2 AA) + revisión manual (teclado, foco, contraste).

## T-13 · Seguridad (ambiente controlado)
- OWASP Top 10 aplicable: tenant isolation (A no lee B), IDOR, broken access control,
  SQLi/XSS, uploads (MIME/tamaño/hash), CSRF, headers, secretos/logs.
- No ejecutar contra producción.

## T-14 · Backup → Restore probado
- Ejecutar `backup.sh` → eliminar entorno temporal → reconstruir → `restore.sh` →
  verificar DB, storage, licencia, installation id, auditoría.
- En PostgreSQL real (no SQLite).

## T-15 · Rendimiento
- Latencia P50/P95/P99, N+1, índices, queries de los endpoints más lentos,
  bundle/lazy loading del frontend; dataset representativo (no 5 registros).

## T-16 · Auditoría fiscal normativa
- Validar IVA/ISLR/IGTF/retenciones, numeración, números de control, notas, libros,
  períodos/cierre contra normativa y Providencias vigentes.
- Verificar inmutabilidad de documentos emitidos (snapshots) en PostgreSQL real.
- Requiere equipo fiscal + documentos oficiales.

## Verificación de timezone/drift en PostgreSQL real (T-06 complemento)
- ORM usa `DateTime(timezone=True)` (mixins) y migraciones compilan offline para
  PostgreSQL (head `0012_numeric_money`, 61 ALTER COLUMN). Falta ejecutar
  `alembic upgrade head` contra una instancia PostgreSQL real y comparar con
  `alembic check` (drift).
