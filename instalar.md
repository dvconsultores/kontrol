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
El intervalo es operacional: ningún trabajo depende de él.