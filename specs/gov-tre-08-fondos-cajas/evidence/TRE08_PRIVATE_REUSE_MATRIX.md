# TRE-08 · matriz de reutilización privada

Solo orientación: el proceso está bloqueado y nada se ha reutilizado. Revisión de nombres de modelo, no de lógica.

| Elemento privado | Clase | Motivo |
|---|---|---|
| `treasury.Cashbox` | FORBIDDEN | Caja de operación comercial, sin resolución, cuentadante ni orden de pago |
| `treasury.CashSession` y `CashSessionMovement` | REUSE_PATTERN_ONLY | Patrón de apertura, movimiento y cierre; semántica de turno de caja |
| Arqueo por sesión | REUSE_PATTERN_ONLY | Diferencia explícita con Decimal; no sustituye el contrato público |
| Documentos | REUSE_SHARED_PRIMITIVE | Infraestructura común, sin cambio |
| Auditoría | REUSE_SHARED_PRIMITIVE | Infraestructura común, sin cambio |
| Reposición y rendición públicas | GOVERNMENT_ADAPTATION_REQUIRED | Sin equivalente privado |
