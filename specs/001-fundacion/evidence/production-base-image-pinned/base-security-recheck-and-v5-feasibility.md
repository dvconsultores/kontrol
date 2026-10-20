# Revalidación OCI, recheck de seguridad y viabilidad de V5 (2026-10-21, OD-CERT-07 = B)

## Revalidación (registro, token anónimo, sha256 del cuerpo verificado)
| Campo | Valor |
|---|---|
| CANDIDATE_INDEX_DIGEST_NOW | `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, igual al aprobado |
| CANDIDATE_AMD64_MANIFEST_DIGEST_NOW | `sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024`, igual |
| CANDIDATE_CONFIG_DIGEST_NOW | `sha256:ce3ff9524414289fc922d9d5dc1de87abc77a39ff2ff5007435839f2af1d7569` |
| PYTHON_VERSION_NOW · CREATED_NOW | 3.13.16 · 2026-10-06T02:05:24Z |
| CANDIDATE_TAG_REBUILT | 0 |
| CPython 3.13.17 | no existe (404) |

## Recheck de seguridad: bloqueante nuevo
**DSA-6572-1** (`ca-certificates`), publicado el 2026-10-20 a las 21:00 UTC en debian-security-announce, msg00487:
- se han comprometido varios certificados de CA intermedia de eMudhra;
- Debian retira las raíces «emSign ECC Root CA - G3» y «Comodo AAA Services root»;
- corregido en trixie con `20250419+deb13u1`; el tracker marca `20250419` como *vulnerable*.

**Medición sobre el sistema de ficheros OCI del candidato** (capas verificadas):
- `ca-certificates 20250419`;
- `/etc/ssl/certs/ca-certificates.crt` (150 certificados) **contiene las dos raíces retiradas**:
  `CN=emSign ECC Root CA - G3` y `CN=AAA Certificate Services` (Comodo).

**Aplicabilidad: SÍ.**
- `UrllibSyncTransport._post` (reto y sincronización con la autoridad de licencias) usa `urllib.urlopen` con el
  contexto por defecto, es decir, el almacén del sistema (`/usr/lib/ssl/cert.pem` → `ca-certificates.crt`).
- No hay `cafile`, `SSL_CERT_FILE` ni certifi en el producto.
- **Mitigación parcial:** las licencias van firmadas con Ed25519 por el propietario (ancla de confianza), el sobre lo
  firma la instalación y hay reto con nonce. Aun así, el canal TLS de licencias confía en raíces comprometidas, lo que
  permite interceptar metadatos y denegar el servicio.

**Estado de las imágenes oficiales:**
- Ninguna imagen oficial de CPython 3.13.16 incluye el arreglo: `3.13.16-slim-trixie` y `3.13.16-trixie` se
  construyeron el 2026-10-06; la última reconstrucción de la familia trixie es de esa fecha.
- **NEW_BASE_SECURITY_BLOCKER = 1.** Por §5: STOP antes de implementar.

Las otras novedades posteriores (xz deb13u2) no aplican.

## Viabilidad de V5 (investigación, sin implementar ni certificar)
- Rootfs `linux/amd64` reconstruido en el scratchpad a partir de las 4 capas verificadas, con whiteouts aplicados.
- CPython de la imagen ejecutado **con el cargador y las bibliotecas de la imagen**:
  `<rootfs>/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 --inhibit-cache --library-path <rootfs libs> <rootfs>/usr/local/bin/python3.13`.

**Resultado:**
- `3.13.16`;
- `ssl.OPENSSL_VERSION` = `OpenSSL 3.5.7 9 Jun 2026` (la de Debian de la imagen);
- `libc_ver` = glibc 2.41;
- **25 bibliotecas cargadas, 0 fuera del rootfs**.

**Clasificación posible:** V5_CPYTHON_SOURCE = **IMAGE_ROOTFS** y V5_RUNTIME_LIB_SOURCE = rootfs del candidato.

**Salvedad medida:** la ruta del bundle de CA es absoluta (`/usr/lib/ssl/cert.pem`) y, sin redirección, resolvería al
**anfitrión**. Una V5 fiel debe fijar `SSL_CERT_FILE` al bundle del rootfs. No es certificación del runtime exacto de la
imagen: falta el `pip install` dentro de la imagen y la ejecución en contenedor.

El rootfs y los blobs se eliminaron del scratchpad al terminar.
