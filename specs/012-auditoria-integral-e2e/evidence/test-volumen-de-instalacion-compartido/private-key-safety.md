# Seguridad del material de clave

Reglas del ciclo: las sondas y las pruebas del arnés solo manejan huellas sha256 truncadas (16 hex), tamaños, modos y rutas
temporales; nunca leen la clave para mostrarla. Las claves son siempre **sintéticas**: las genera
`get_or_create_installation` (Ed25519) en bases en memoria durante la prueba y mueren con su volumen.

| Comprobación | Resultado |
|---|---|
| TV-11: salida estándar, error estándar e informe JSON de las sondas sin `PRIVATE KEY` ni `-----BEGIN`; huellas `^[0-9a-f]{16}$` | PASS (y el mutante M-10, que inyectaba el PEM en el informe, muere) |
| Escaneo de la evidencia, el delta, el conftest y las pruebas nuevas: `BEGIN (PRIVATE|EC|RSA|OPENSSH) KEY`, `PRIVATE KEY-----`, URLs `postgresql+psycopg2://` con credenciales, `/home/<usuario>/`, `password`, contraseña QA, `KTL-VE-XXXXXXXX-XXXX` reales | 0 coincidencias reales (dos falsos positivos: el nombre de fichero `test_password_reset.py` en la matriz y el ejemplo `postgresql+psycopg2://...` del docstring preexistente de `make_engine`) |
| Rutas | temporales sintéticas normalizadas como `<tmp>`; URL de PostgreSQL de QA enmascarada `://***@` |
| `PRIVATE_KEY_CONTENT_IN_EVIDENCE` | **0** |
| `SECRET_EXPOSURE` | **0** |
| Egress a DeepSeek (T04, 2 llamadas) | `ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0 REAL_PATHS=0` |
