# Suite de caracterización del host

Estas pruebas fijan evidencia sobre primitivas del sistema operativo; no
prueban un runtime de ektel, que todavía no existe.

Ejecutar desde la raíz:

```sh
python3 -m unittest discover -s tests/escape -v
```

La suite sólo contiene casos acotados y recuperables. Fork bombs, D-state,
presión extrema de memoria y muerte deliberada del proceso de pruebas quedan
excluidos hasta disponer de un entorno desechable específico.

Las expectativas son por plataforma. Un cambio de comportamiento del OS debe
revisarse como evidencia nueva, no “arreglarse” relajando la aserción.
