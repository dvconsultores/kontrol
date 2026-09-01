# MATRIZ FUNCIONAL DEL CONTEXTO DE EMPRESA — N6

| Capacidad | Una empresa | Varias empresas | Multi-pestaña | Acceso revocado | Empresa inactiva | Veredicto |
|---|---|---|---|---|---|---|
| Resolución al arrancar | automática | pide elegir | independiente | se descarta | no se restaura | **PASS** |
| Selector visible | contexto sin control | desplegable | por pestaña | se retira | no se ofrece | **PASS** |
| Cabecera en las peticiones | siempre | la elegida | la de cada pestaña | ninguna | ninguna | **PASS** |
| Preferencia | irrelevante | se recuerda | no aplasta la pestaña | se borra | se borra | **PASS** |
| Caché | única | separada | separada | descartada | descartada | **PASS** |
| Pantalla de negocio | se pinta | tras elegir | por pestaña | se detiene | se detiene | **PASS** |

## Decisiones y por qué

**Con una sola empresa no se muestra un control de selección.** Un desplegable
que solo puede dar una respuesta es ruido; el contexto sigue visible porque
saber en qué empresa se opera nunca sobra.

**Con varias y sin preferencia válida no se elige la primera.** Decidir por el
usuario en qué empresa opera es exactamente lo que no debe hacerse: la primera
por orden de creación no significa nada.

**La preferencia se restaura solo si sigue autorizada y activa.** Ayer con
acceso a B y hoy sin él, la preferencia se descarta y se borra. No concede nada:
se contrasta contra la lista que devuelve el servidor.

**El contexto de la pestaña gana sobre la preferencia.** La preferencia es del
navegador; el contexto es de esta pestaña. Si mandara la preferencia, abrir una
segunda pestaña y cambiar de empresa allí arrastraría a la primera.

**Sin empresa resuelta no se pinta ninguna pantalla de negocio.** Pintarla
dispararía peticiones de empresa sin saber cuál, y la respuesta a «¿de qué
empresa son estos datos?» sería «de ninguna en concreto».

## El caso de cero empresas

Un usuario mal configurado —sin `UserScope` en ninguna empresa activa— recibe un
estado explicado, no una pantalla rota ni un bucle de peticiones. No se disparan
peticiones de empresa porque no hay ninguna que enviar.
