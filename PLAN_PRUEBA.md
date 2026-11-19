# Plan de prueba piloto

## Objetivo del piloto

Seleccionar un perímetro pequeño de una ciudad, descubrir negocios dentro de él y construir una tabla georreferenciada que luego pueda enriquecerse con visión artificial.

## Fase 1 — Perímetro + Google Places

1. Abrir la aplicación.
2. Dibujar un polígono de 4–8 cuadras.
3. Generar puntos de barrido cada 150 m.
4. Consultar Google Places con radio de 120 m.
5. Deduplicar por Place ID.
6. Conservar solo establecimientos dentro del polígono.
7. Exportar CSV.

### Resultado esperado

- nombre
- dirección
- coordenadas
- tipo de establecimiento
- estado
- website
- enlace Google Maps

## Fase 2 — Validación visual

Sobre imágenes que tengamos derecho a analizar:

- detectar fachada comercial;
- detectar aviso comercial;
- detectar vitrina;
- ejecutar OCR del aviso;
- comparar nombre OCR con el nombre de Google Places.

## Criterio inicial de éxito

En un piloto pequeño:

- recuperar una muestra útil de negocios del perímetro;
- obtener dirección y nombre para la mayoría;
- identificar candidatos sin sitio web;
- dejar lista la tabla para enriquecerla con visión.

## Fase 3 — Oportunidad comercial

Crear una columna `oportunidad_web` combinando, por ejemplo:

- no tiene website en Places;
- fachada/aviso comercial confirmado;
- negocio operativo;
- nombre OCR consistente;
- categoría comercial prioritaria.
