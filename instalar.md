/opt/kontrol/
├── compose.yaml
├── kontrol.py          # install.sh calls: python3 kontrol.py preflight
├── .env                # created from .env.example
└── scripts/
    ├── install.sh
    ├── install-scheduler.sh   # temporizador del planificador (Spec 047 · ADR-D0-015)
    ├── scheduler/             # plantillas systemd: kontrol-scheduler.service y .timer
    ├── backup.sh
    ├── restore.sh
    ├── update.sh
    └── diagnose.sh

Planificador de plataforma (una vez por instalación de cliente, en su host):

    KONTROL_INSTANCE=<cliente> KONTROL_SCHEDULER_INTERVAL=<intervalo systemd, p. ej. 5min> \
        sudo -E scripts/install-scheduler.sh

El temporizador solo invoca `python3 kontrol.py scheduler-tick`, que ejecuta
`python -m app.modules.scheduler tick` dentro del backend de esta instalación.

## Segundo factor (Spec 002)

Generar `KONTROL_MFA_KEYS` antes del primer arranque:

    python3 -c "import base64, secrets; print('k1:' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))"

Custodiar esta clave aparte de la base de datos y de sus copias. Mantener el reloj del servidor sincronizado por NTP. Los runbooks de rotación de clave y rotura de cristal están en `specs/001-fundacion/backup-restore-plan.md` §7.
El intervalo es operacional: ningún trabajo depende de él.

## Copias de seguridad

Generar y custodiar `KONTROL_BACKUP_KEY` aparte, igual que `KONTROL_MFA_KEYS`; sin esta clave la copia es irrecuperable. Crear, verificar y restaurar con `python3 kontrol.py backup`, `python3 kontrol.py backup-verify <paquete>` y `python3 kontrol.py restore <paquete> --expected-installation-id <ID>`. Procedimiento y códigos de salida en `specs/001-fundacion/backup-restore-plan.md` §4 y §8.