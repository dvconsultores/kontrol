# SPEC 054 · Delta dirigida — OBS-11 (enlace cruzado)
La delta completa vive en `specs/010-licenciamiento-central/spec010-obs11-sync-time-anchor-delta.md`. Para el arnés: una
constante de módulo evaluada al importar (`SERVER_TIME = now + 5 min`) no es una frontera de operación válida para una
aserción contra un valor persistido por una operación posterior con regla monótona; la referencia debe capturarse en la
operación (el transporte falso de cada prueba). Patrón registrado para 054; no hay cambio en `conftest.py`.
