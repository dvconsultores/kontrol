# Viabilidad de ClamAV en el QA canónico (sin instalar nada)

| Registro | Valor |
|---|---|
| `CLAMAV_PACKAGE_AVAILABLE` | sí: Debian trixie `clamav 1.4.3+dfsg-1` (candidato; `apt-cache policy`), `clamav-freshclam`, `libclamav12` (34 MB instalado), `clamav-base`; la misma versión 1.4.3 que certificó la Spec 046 |
| `CLAMSCAN_EXECUTABLE_EXPECTED_PATH` | `/usr/bin/clamscan` (paquete) o la ruta que se exporte en `KONTROL_CLAMSCAN_PATH` (extracción sin privilegios) |
| Privilegios | `apt-get install` exige `sudo` con contraseña (no disponible para el agente; ninguna instalación se ejecuta en este ciclo). El closeout lo resolvió «extrayendo el `.deb` sin privilegios» (`dpkg -x` a un prefijo de usuario + `KONTROL_CLAMSCAN_PATH`/`KONTROL_CLAMAV_DB`), **método no guionizado en el repositorio** |
| `DATABASE_SIGNATURES_REQUIRED` · `FRESHCLAM_REQUIRED` · `NETWORK_REQUIRED` | sí (`main.cvd`/`daily.cvd`/`bytecode.cvd`, ≈ 200–300 MB; EICAR está en la base principal) · sí para obtenerlas y actualizarlas (o copia manual de `.cvd`) · sí (`database.clamav.net`; una petición `HEAD` desde aquí devolvió 403: el CDN exige el cliente `freshclam`, no concluyente) |
| `DAEMON_REQUIRED` · `CLI_ONLY_SUPPORTED` | no · sí (el adaptador usa `clamscan`) |
| `STARTUP_COST` · `APPROX_TEST_RUNTIME_IMPACT` | `clamscan` carga la base en cada invocación: el closeout midió 10–17 s por prueba de malware en E2E y 31,6 s la carga E2E más lenta; en backend, 35 subidas × ~5–15 s ≈ 3–9 min más por suite (estimación, no medida) |
| `CONTAINER_IMAGE_IMPACT` · `OFFLINE_CI_IMPACT` | +~35 MB de binarios +~300 MB de firmas por imagen; sin red no hay firmas ni actualizaciones (determinismo: fijar una fecha de firmas y versionarlas) |
| `SECURITY_UPDATE_REQUIREMENT` · `LICENSE/COMPLIANCE` | firmas que caducan (freshclam diario) · GPLv2 (ClamAV) sin impacto en el producto (proceso externo) |

Conclusión: técnicamente viable (paquete disponible), pero exige privilegios o un prefijo de usuario documentado, red para las
firmas, una política de actualización y asumir minutos de más por suite. Es una decisión de infraestructura de QA de la dueña.
