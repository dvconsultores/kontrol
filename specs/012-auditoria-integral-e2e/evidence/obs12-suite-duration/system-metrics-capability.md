# Capacidad de métricas del sistema (solo lectura, sin dependencias nuevas)
| Registro | Valor |
|---|---|
| `LOAD_AVAILABLE` | sí: `/proc/loadavg` (1/5/15 min, hilos ejecutables/total) |
| `MEMORY_AVAILABLE` | sí: `/proc/meminfo` (`MemAvailable`, `MemTotal` 15,0 GiB) |
| `CPU_AVAILABLE` | sí: `/proc/stat` (`cpu` acumulado → utilización por delta; `procs_running`); 12 CPU lógicas |
| `DISK_IO_AVAILABLE` | sí: `/proc/diskstats` (sectores leídos/escritos del dispositivo `nvme0n1` → deltas) |
| `PROCESS_RSS_AVAILABLE` | sí: `resource.getrusage(RUSAGE_CHILDREN)` desde un lanzador Python de la biblioteca estándar (`ru_maxrss`, CPU usuario/sistema, cambios de contexto voluntarios/involuntarios, bloques de E/S) |
| `CONTEXT_SWITCH_AVAILABLE` | sí: `/proc/stat` `ctxt` (global) y `getrusage` (del árbol de pytest) |
| `/usr/bin/time -v` | **no instalado**; se sustituye por `getrusage` (sin dependencia nueva) |
| `vmstat` | presente (no necesario) |
| Excluido por contrato | IP, interfaces, VPN, nombre de equipo, usuario, rutas personales (FR-O12-008) |
Precedente en el repositorio: `qa/e2e_corrida.py` ya registra `desvio_de_reloj` (pared vs monotónico) y `huella_de_red`
saneada en el manifiesto E2E; el contrato de medición de OBS-12 sigue ese patrón.
