# P25 · la prueba sigue forzando la carrera y sigue sin aceptar un 500

- La prueba objetivo no cambia: `Barrier(2)` para que las dos peticiones salgan a la vez; `sorted(results) == [200, 409]`;
  `total == 1`. Un 500 mata el hilo (`TestClient` relanza) y la aserción falla: no se acepta.
- ACS-04 añade, en el arnés, la carrera con entrelazado controlado (los dos INSERT a la vez) y exige exactamente un
  `IntegrityError` y ningún otro error.
- ACS-05 demuestra que un error de bloqueo no se confunde con un duplicado: `OperationalError` no es `IntegrityError` y
  `es_violacion_unica` lo rechaza.
- La barrera de `before_cursor_execute` vive solo en ACS-04 (prueba de arnés) y en la POC; no en la prueba objetivo ni
  en el producto.
