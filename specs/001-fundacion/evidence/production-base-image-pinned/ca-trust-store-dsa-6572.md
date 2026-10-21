# Almacén de confianza — DSA-6572-1 (2026-10-21, OD-CERT-08 = R1-DYNAMIC-EXACT-PIN)

## Selección de la versión (trixie-security, cadena de confianza verificada)
| Paso | Resultado |
|---|---|
| `InRelease` de trixie-security | `gpgv` con `/usr/share/keyrings/debian-archive-keyring.gpg`: **firma correcta** de «Debian Security Archive Automatic Signing Key (13/trixie)» (2026-10-20 23:32:30 CEST) |
| `main/binary-amd64/Packages.xz` | sha256 `bcf7a4c2f26bd396d8b91f85d00984bdfc3e40452bdc22ca7b2877c8fadf9cc1`, presente en el `InRelease` firmado |
| CA_CERTIFICATES_AVAILABLE_VERSIONS | `20250419+deb13u1`, la única en trixie-security |
| CA_CERTIFICATES_EXPECTED_VERSION · SELECTED · VERSION_ADVANCED | `20250419+deb13u1` · `20250419+deb13u1` · 0 |
| `.deb` | `pool/updates/main/c/ca-certificates/ca-certificates_20250419+deb13u1_all.deb`; sha256 `c10585ac22c7f617a73d394eea29ba71d0356f350ae973b19043d1b017f80f54`, que **coincide** con `Packages`; `Package: ca-certificates`, `Version: 20250419+deb13u1`, `Architecture: all`, `Depends: openssl (>= 1.1.1), debconf` |
| UPSTREAM_REBUILD_WITH_DSA6572_FIX | 0: el índice `70729b46…` no cambió y la imagen sigue siendo de 2026-10-06 |

## Contenido del paquete corregido
- **FIXED_CA_PACKAGE_CONTENTS_VERIFIED = 1.**
  - 148 certificados en `usr/share/ca-certificates/mozilla/`.
  - Por nombre de fichero y por *subject* (`openssl x509`), no hay ni «emSign ECC Root CA - G3» ni «AAA Certificate
    Services» (Comodo).
- Diferencia con el paquete de la imagen (`ca-certificates.list` de dpkg frente a `dpkg-deb -c`):
  - **retirados** `Comodo_AAA_Services_root.crt` y `emSign_ECC_Root_CA_-_G3.crt`;
  - **añadidos: ninguno**.

## Reconstrucción del bundle efectivo (V5)
- **FIXED_CA_BUNDLE_RECONSTRUCTED = 1**, con este método, sobre el rootfs del candidato:
  1. `dpkg-deb -x` del paquete corregido.
  2. Borrado de los ficheros del paquete viejo ausentes en el nuevo, igual que hace dpkg al actualizar: los dos `.crt`
     retirados.
  3. Ejecución del `update-ca-certificates` **del propio paquete** con
     `--sysroot <rootfs> --hooksdir "" --fresh` y el `ca-certificates.conf` de la imagen.
- Resultado: «148 added, 0 removed»; avisa de que las dos entradas retiradas siguen en la conf sin fichero y las omite.
- **Paso no ejecutado:** la reescritura de `ca-certificates.conf` por debconf en el `postinst`. Es neutral para este
  cambio: la actualización no añade ningún certificado (0 nuevos), así que la conf no puede habilitar nada nuevo, y las
  dos entradas retiradas no tienen fichero.
- Bundle reconstruido (`<rootfs>/etc/ssl/certs/ca-certificates.crt`): 148 certificados;
  REMOVED_ROOTS_ABSENT_IN_V5_BUNDLE = 1.
- Comprobación en ejecución (V5): `ssl.create_default_context().get_ca_certs()`, el contexto que usa `urllib` en el
  transporte de licencias, carga 148 CA, **ninguna** de las dos retiradas.
  - `ssl.get_default_verify_paths().cafile` apunta al bundle del rootfs (`SSL_CERT_FILE`).
  - **V5_CA_TRUST_SOURCE = bundle del rootfs reconstruido**; nunca el almacén del anfitrión.

## Clasificación
| Indicador | Valor |
|---|---|
| DSA6572_APPLICABLE | 1 |
| DSA6572_REMEDIATED | 1: pin exacto en el Dockerfile y contenido verificado |
| REMOVED_ROOTS_ABSENT_IN_FIXED_PACKAGE | 1 |
| REMOVED_ROOTS_ABSENT_IN_V5_BUNDLE | 1 |
| REMOVED_ROOTS_ABSENT_IN_IMAGE_RUNTIME | NOT MEASURED (sin Docker) |
| EXACT_IMAGE_CA_RUNTIME_CERTIFIED | 0 |

## Hallazgo relacionado en el lock (no absorbido)
**PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2** (`certifi`, mismo incidente eMudhra; publicado 2026-10-20 21:41Z):
- El rango OSV marca como afectada la versión `certifi 2026.10.18` del lock (corregida en 2026.10.19), pero el propio
  texto del aviso dice que 2026.10.18 **retiró todas las raíces emSign**.
- **Medido:** el `cacert.pem` instalado (117 certificados) no contiene ninguna raíz emSign ni AAA.
- Además, el producto no usa certifi: 0 imports de certifi, httpx o requests. certifi llega solo por httpx y httpcore,
  que son dependencias de pruebas, y licencias usa `urllib` con el almacén del sistema.
- **Aplicable: 0** (contenido y uso). pip-audit lo sigue listando: 1 hallazgo.
- Para eliminarlo hace falta mover el corte del lock, que es una ruta prohibida en este ciclo. Se registra como
  **LOCK-CERTIFI-PYSEC-2026-4320**.
