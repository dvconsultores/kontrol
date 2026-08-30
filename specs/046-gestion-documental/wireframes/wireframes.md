# WIREFRAMES — SPEC 046

Principio: **la carga es el momento en que el usuario duda.** Estas pantallas
dicen qué se aceptó, qué se rechazó y por qué, sin obligar a adivinar.

---

## W-046-01 · Biblioteca documental · `/documentos`

```
┌──────────────────────────────────────────────────────────────────────┐
│ Documentos                                                           │
│ Documentos y evidencias de la empresa activa      [+ Nuevo documento]│
├──────────────────────────────────────────────────────────────────────┤
│ Buscar [__________]  Tipo [Todos ▾]  Estado [Todos ▾]  Vence [ ___ ] │
├──────────────────────────────────────────────────────────────────────┤
│ Documento              Tipo             Vence      Estado    Acc.    │
│ Packing list PO-1042   PACKING_LIST     —          Activo    👁 ⤓   │
│ Permiso sanitario 887  PERMISO_SANIT.   12/11/26   Activo    👁 ⤓   │
│ Certificado origen     CERT_ORIGEN      02/09/26 ⚠ Activo    👁 ⤓   │
│ Guía de despacho 55    GUIA_DESPACHO    —          Archivado 👁     │
├──────────────────────────────────────────────────────────────────────┤
│                                            ‹ 1 2 3 ›  84 documentos  │
└──────────────────────────────────────────────────────────────────────┘
```

- El **vencimiento** es columna de primer nivel: es la razón por la que 044 y 047
  consultarán esta capacidad.
- El aviso ⚠ marca lo próximo a vencer. `EXPIRED` **no** es un estado: se deriva
  de la fecha, y por eso se muestra junto a ella y no en la columna de estado.
- Nombres largos se truncan con el completo en `title`; nunca ensanchan la tabla.

## W-046-02 · Detalle · `/documentos/{id}`

```
┌──────────────────────────────────────────────────────────────────────┐
│ Documentos › Permiso sanitario 887                                   │
│ Permiso sanitario 887                          [Nueva versión] [⤓]   │
├──────────────────────────────────────────────────────────────────────┤
│ Tipo        PERMISO_SANITARIO       Emisor    Ministerio de Salud    │
│ Número      887-2026                Emitido   12/11/2025             │
│ Estado      Activo                  Vence     12/11/2026             │
│                                                                      │
│ ── Archivo vigente ────────────────────────────────────────          │
│   permiso-887.pdf · 1,2 MB · PDF · versión 2                         │
│   Integridad  9f2c8a…d41b        Seguridad  Sin analizar             │
│                                                  └ política del tipo │
│                                                                      │
│ ── Vinculado a ────────────────────────────────────────────          │
│   Permiso regulatorio PI-2026-44        Evidencia    🔒 congelado    │
│   Despacho SH-1180                      Soporte      [Desvincular]   │
├──────────────────────────────────────────────────────────────────────┤
│  ⓘ El vínculo con PI-2026-44 está congelado en la versión 1: el      │
│    permiso se usó con ese archivo y no se reinterpreta.              │
└──────────────────────────────────────────────────────────────────────┘
```

- **«Sin analizar» se muestra**, no se oculta. Afirmar seguridad que no se
  comprobó sería peor que declarar la ausencia.
- El candado explica **por qué** ese vínculo no se toca. Un control deshabilitado
  sin motivo es peor que uno habilitado que falla.

## W-046-03 · Historial de versiones

```
┌──────────────────────────────────────────────────────────────────────┐
│ Permiso sanitario 887 · Versiones                                    │
├──────────────────────────────────────────────────────────────────────┤
│ V  Fecha        Archivo             Integridad   Motivo       Estado │
│ 2  30/08/2026   permiso-887.pdf     9f2c8a…      Corrección   Vigente│
│ 1  12/11/2025   permiso-887-v1.pdf  4b71ee…      —            Superad│
│                                                               🔒     │
├──────────────────────────────────────────────────────────────────────┤
│  ⓘ Las versiones superadas no se editan ni se borran: los procesos   │
│    que las usaron siguen apuntando a ellas.                          │
└──────────────────────────────────────────────────────────────────────┘
```

Cada versión muestra su hash: es lo que hace verificable la evidencia.

## W-046-04 · Carga de archivo — el momento crítico

```
┌──────────────────────────────────────────────────────────────────────┐
│ Nueva versión de: Permiso sanitario 887                              │
├──────────────────────────────────────────────────────────────────────┤
│   ┌────────────────────────────────────────────────────┐             │
│   │   Arrastre un archivo o                            │             │
│   │              [ Seleccionar archivo ]  ← foco       │             │
│   └────────────────────────────────────────────────────┘             │
│                                                                      │
│   Tipos admitidos: PDF, JPG, PNG      Tamaño máximo: 10 MB           │
│   └ los declara PERMISO_SANITARIO, no la pantalla                    │
│                                                                      │
│   Seleccionado:  permiso-887.pdf · 1,2 MB · PDF          [Quitar]    │
│   Motivo del reemplazo * [_________________________________]         │
│                                                                      │
│   ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  Subiendo…                                     │
│                                                                      │
│                                  [ Cancelar ]   [ Subir ]            │
└──────────────────────────────────────────────────────────────────────┘
```

- El botón **existe y recibe foco**: arrastrar y soltar es un extra, nunca el
  único camino (§161, FR-046-093).
- Los límites se muestran **antes** de elegir, y provienen del tipo, no de la
  pantalla.
- La barra avanza solo si el progreso es real; si no se conoce, se muestra
  «Subiendo…» sin porcentaje (§99).

## W-046-05 · Errores de carga — diferenciados

```
┌──────────────────────────────────────────────────────────────────────┐
│ ✕ No se pudo subir el archivo                                        │
│                                                                      │
│   El archivo dice ser PDF pero su contenido no lo es.                │
│   Tipos admitidos para PERMISO_SANITARIO: PDF, JPG, PNG.             │
│                                                     [ Elegir otro ]  │
└──────────────────────────────────────────────────────────────────────┘
```

Un mensaje por causa: tamaño, tipo no admitido, contenido que no coincide,
nombre inseguro, archivo infectado, almacenamiento no disponible, sin permiso,
petición repetida. **Nunca «error desconocido»** (§100, FR-046-095).

## W-046-06 · Componente de adjuntos reutilizable

Lo que otras Specs incrustarán, sin implementar nada propio (§97):

```
┌─ Documentos ─────────────────────────────────────────────┐
│  packing-list.pdf      PACKING_LIST    v1     ⤓          │
│  foto-daño.jpg         EVIDENCIA       v1     ⤓  🔒      │
│                                                          │
│  [ + Adjuntar documento ]                                │
└──────────────────────────────────────────────────────────┘
```

Recibe `resource_type` y `resource_id`; resuelve por sí mismo lista, carga,
descarga, estado y versión. El dominio que lo usa no conoce el almacenamiento.

## W-046-07 · Tipos documentales · `/documentos/tipos`

Página completa. Muestra, por tipo: extensiones y MIME admitidos, tamaño máximo,
si versiona, si exige vigencia, si audita descargas y si exige análisis.

```
│  ⓘ Sin tipos admitidos declarados, un tipo documental no acepta      │
│    ningún archivo. La lista vacía significa «ninguno», no «todos».   │
```

Esa frase está en la pantalla a propósito: es la clase de valor por defecto que,
mal entendido, convierte un repositorio en un vector de distribución.

## W-046-08 · Previsualización en pantalla estrecha

```
│  El documento tiene 4,1 MB. Ábralo en una vista dedicada o           │
│  descárguelo.                                                        │
│              [ Abrir vista completa ]   [ Descargar ]                │
```

No se incrusta un PDF grande en 320 px: se ofrece la alternativa usable (§106).
La previsualización exige **el mismo permiso** que la descarga (§107).
