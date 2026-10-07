# Checklist — Autoridad Central Fase 1

- [x] HEAD `52b133c` reconciliado · develop · árbol limpio · orquestación 11/11
- [x] dueña SPEC004 · D0-06 y ADR-D0-006 recuperados · delta de `revision` recuperado · paquete y canonicalización recuperados
- [x] sync del cliente localizado: ruta, cuerpo, cabeceras; **autenticación inexistente → bloqueo separado**
- [x] identidad de instalación conocida · ubicación `central_authority/` · FastAPI/PostgreSQL · base central independiente · base y Compose del cliente intactos
- [x] clave: configuración `KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM`, nunca en repo, fallo cerrado en prod, firmante sintético explícito
- [x] registro, unicidad, linaje, libro append-only, alcance de `revision`, primera = 1, reemisión monótona, concurrencia sin MAX+1 inseguro
- [x] constraints, índices, migraciones, instalación limpia, CLI, sin API admin pública, atribución de operador, firma, `kid`, health, redacción, auditoría
- [x] compatibilidad del cliente clasificada (caso A) · rotación, comparación cliente y reverificación excluidas
- [x] pruebas, concurrencia, mutaciones, tareas DeepSeek acotadas · `MATERIAL OQ = 1` (sync, separado) · `UNKNOWN = 0` · trazabilidad 100 %
