# CHECKLIST — SPEC 046

## Modelo

- [ ] `Document`, `DocumentVersion`, `StoredFile`, `DocumentLink` con FK reales
- [ ] `DocumentCategory` y `DocumentType` por empresa, catálogo **vacío**
- [ ] `file_metadata` evoluciona a `stored_files`; sin tabla paralela
- [ ] Estado del documento y del archivo en columnas distintas
- [ ] `EXPIRED` derivado, no persistido
- [ ] `document_number` sin unicidad global; única parcial por tipo y empresa
- [ ] Registro cerrado de tipos de recurso; sin texto libre

## Almacenamiento

- [ ] Interfaz de proveedor con implementación intercambiable
- [ ] Proveedor de sistema de archivos sobre el volumen existente
- [ ] Ningún binario en PostgreSQL
- [ ] `storage_key` opaca, generada por el servidor
- [ ] Escribir → verificar → confirmar
- [ ] Verificación de integridad que detecta metadata sin binario
- [ ] Credenciales como secretos: nunca en base, frontend ni registros

## Subida

- [ ] El nombre del usuario nunca es ruta
- [ ] `original_filename` conservado; saneado solo para mostrar
- [ ] MIME declarado y detectado, guardados por separado
- [ ] Discrepancia rechazada salvo política del tipo
- [ ] Lista blanca vacía significa **ninguno**
- [ ] Tamaño máximo por tipo, rechazo temprano
- [ ] SHA-256 del servidor; el del cliente ignorado
- [ ] Idempotencia: sin versiones duplicadas
- [ ] Ejecutables y comprimidos rechazados por defecto

## Descarga y previsualización

- [ ] Autorización sobre la entidad vinculada
- [ ] 404 en vez de 403 al no tener acceso
- [ ] Sin URL públicas permanentes
- [ ] URL firmadas con expiración corta, no persistidas ni registradas
- [ ] Previsualización con el mismo permiso que la descarga
- [ ] SVG, HTML y comprimidos siempre como descarga
- [ ] Sin ejecución de contenido activo
- [ ] `Cache-Control: private, no-store`

## Versionado e inmutabilidad

- [ ] Número de versión asignado por el servidor
- [ ] Una sola versión vigente por documento
- [ ] Versión superada inmutable
- [ ] Original conservado byte a byte
- [ ] Vínculo congelado apunta a la versión usada
- [ ] Vínculo congelado no se desvincula

## Seguridad del archivo

- [ ] Estados de análisis modelados
- [ ] No `CLEAN` no se entrega
- [ ] Sin analizador, `SKIPPED` **declarado** en la respuesta
- [ ] Resultado del análisis auditado

## Legado

- [ ] Las 9 columnas se conservan intactas
- [ ] **0 documentos creados** desde texto
- [ ] Hash sin binario no genera documento
- [ ] Archivo faltante reportado, no inventado
- [ ] `reporting` sin cambios

## Transversalidad

- [ ] Un solo mecanismo de archivos en todo el sistema
- [ ] Componente de adjuntos reutilizable
- [ ] Contrato de la Spec 045 satisfecho **sin cambiar su modelo**
- [ ] Contratos para las 8 Specs bloqueadas
- [ ] Ningún proceso consumidor implementado
- [ ] Sin RBAC, auditoría, aprobaciones ni notificaciones propias

## Verificación final

- [ ] PostgreSQL 18.x **y almacenamiento real**
- [ ] Las 20 amenazas con prueba
- [ ] axe WCAG 2.2 AA; carga operable solo con teclado
- [ ] Responsive con nombres de archivo largos
- [ ] Cross-browser en tres navegadores
- [ ] 0 tipos ni extensiones codificados
- [ ] 0 respuestas con `storage_key`
