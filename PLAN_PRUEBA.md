# Plan de prueba piloto

## Objetivo

Seleccionar un perímetro pequeño de una ciudad y obtener una lista de comercios del área para preparar un recorrido visual posterior.

## Piloto 1 — Google Maps + Places Aggregate

1. Dibujar un polígono de 4–8 cuadras.
2. Consultar Places Aggregate API usando el polígono como `customArea`.
3. Recuperar hasta 100 Place IDs.
4. Mostrar detalles en vivo sobre Google Maps.
5. Guardar únicamente los Place IDs.

### Criterio de éxito

- el polígono coincide con el sector deseado;
- la aplicación devuelve comercios útiles;
- los resultados pueden visualizarse en el mapa;
- los Place IDs quedan disponibles para validación posterior.

## Piloto 2 — recorrido visual

Capturar imágenes con una fuente autorizada para visión artificial.

Por imagen:

- coordenadas propias;
- fachada comercial sí/no;
- aviso comercial sí/no;
- vitrina sí/no;
- texto OCR;
- confianza.

## Piloto 3 — consolidación

Cruzar:

```text
detección visual propia
+
OCR propio
+
Place ID Google
+
validación de website en vivo
```

Resultado: identificar negocios activos con fachada comercial y baja presencia digital.
