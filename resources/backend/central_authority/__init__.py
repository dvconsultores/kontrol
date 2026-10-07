"""Autoridad Central de Licencias de KONTROL — Fase 1 (Spec 004, componente desplegable).

Servicio del propietario, aislado de cualquier instalación cliente: registro de instalaciones,
libro de emisiones, `revision` firmada y paquete firmado con la clave privada del propietario.
Comparte con el cliente únicamente el contrato puro `app.core.license_contract`.
"""

__version__ = "1.0.0"
