# Coherencia de intérprete y sistema, y revisión de seguridad de la base (2026-10-21)

**Método:**
- Capas OCI descargadas al scratchpad y verificadas por sha256; después se borraron.
- Lectura de `include/python3.13/patchlevel.h` y del `var/lib/dpkg/status` final, sin ejecutar nada de la imagen.
- Clase de evidencia: **MEASURED_OCI_FILESYSTEM**.

## Contenido de los candidatos

| Candidato (amd64) | CPython | glibc (`libc6`) | `libssl3t64` / `openssl` | `libpcre2-8-0` |
|---|---|---|---|---|
| `3.13.15-slim-trixie@sha256:7c61056e…` | **3.13.15** | 2.41-12+deb13u4 | 3.5.7-1~deb13u2 | 10.46-1~deb13u2 |
| `3.13.16-slim-trixie@sha256:70729b46…` | **3.13.16** | 2.41-12+deb13u4 | **3.5.7-1~deb13u3** | **10.46-1~deb13u3** |

- Los dos candidatos solo difieren en esos paquetes (dpkg, 87 paquetes por imagen).
- glibc 2.41 ≥ 2.34 en los dos, así que el wheel `manylinux_2_34` de cryptography 50.0.2 se instala como wheel.
- libmagic: `libmagic1t64` y `libmagic-mgc` 1:5.46-5 están disponibles en trixie main.

## Seguridad que separa a los dos candidatos

| Fuente | Corrige | ¿Aplica a KONTROL? |
|---|---|---|
| **openssl 3.5.7-1~deb13u3** (DSA, 2026-09-29) | CVE-2026-35189 (asignación excesiva al procesar CRLDP relativos en la caché de extensiones X.509) | **SÍ, severidad baja:** afecta a clientes TLS en un handshake normal ante un certificado manipulado, y el backend es cliente TLS del servidor de licencias (`UrllibSyncTransport._post`, `urllib.urlopen` con el OpenSSL del sistema). Riesgo: denegación de servicio por memoria |
| | CVE-2026-84782, -75806 (DTLS); -35191, -75804, -84784, -42772, -54873 (QUIC); -54875, -77696 (SM2); -75805 (CMP); -72897 (`SSL_set_SSL_CTX` en servidor); -54872 (firma ECDSA con curvas no NIST) | no: el producto no usa esos protocolos ni firma con el OpenSSL del sistema, y el TLS de servidor lo termina nginx |
| pcre2 10.46-1~deb13u3 | GHSA-r9hj-j2rw-4q3m (pila JIT) | no: lo usan utilidades del sistema, no el runtime de Python |
| CPython 3.13.16 | CVE-2026-82049 y escape de directorios en los filtros de tarfile; límites de zipfile; CVE-2026-19445 (`sni_callback`); validación de `server_hostname` en `wrap_bio`/`start_tls`; CVE-2026-15806 (`HTTPPasswordMgr`); expat incluido 2.8.5; caída al formatear | no: 0 usos de tarfile, zipfile, xml, `HTTPPasswordMgr`, `wrap_bio`, `start_tls` y TLS de servidor. La imagen oficial enlaza el expat del sistema |

## Posterior incluso a 3.13.16 (2026-10-06)

| Fuente | Corrige | ¿Aplica a KONTROL? |
|---|---|---|
| xz-utils 5.8.1-1+deb13u2 | GHSA-5qpq-xqfv-j9pg | no: el producto no usa `lzma` |
| ca-certificates 20250419+deb13u1 (trixie-updates) | actualización del almacén de confianza | NOT MEASURED: changelog no recuperable |

## Resultado

| Indicador | Valor |
|---|---|
| BASE_IMAGE_SECURITY_BLOCKER_FOUND (candidato 3.13.15) | **1**: OpenSSL del sistema con CVE-2026-35189 aplicable y corregido, y además regresión frente a lo desplegado hoy |
| BASE_IMAGE_SECURITY_BLOCKER_FOUND (candidato 3.13.16) | 0 |
| BASE_OS_SECURITY_COMPLETE_AUDIT | NOT MEASURED (sin SBOM ni escáner completo) |
