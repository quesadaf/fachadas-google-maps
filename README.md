# Fachadas Google Maps — piloto comercial

MVP para seleccionar un **perímetro sobre Google Maps**, generar puntos de barrido, consultar negocios mediante **Google Places API (New)** y exportar una tabla preparada para una segunda etapa de visión artificial (fachada, aviso comercial, vitrina y OCR).

## Qué hace hoy

1. Abre un mapa de Google en el navegador.
2. Permite marcar un polígono haciendo clic en sus vértices.
3. Genera una cuadrícula de puntos dentro del perímetro.
4. Consulta Google Places alrededor de esos puntos.
5. Elimina duplicados por `place_id` y descarta resultados fuera del polígono.
6. Muestra nombre, dirección, tipo, web y enlace a Google Maps.
7. Guarda y permite descargar un CSV.

Las columnas de visión (`fachada_comercial`, `aviso_comercial`, `vitrina`, `nombre_ocr`) quedan inicialmente como pendientes.

## Arquitectura del piloto

```text
Google Maps (selección del perímetro)
              ↓
      polígono lat/lng
              ↓
     cuadrícula de barrido
              ↓
     Google Places API New
              ↓
 candidatos comerciales + dirección + web
              ↓
             CSV
              ↓
   [Fase 2: fuente de imágenes permitida]
              ↓
      YOLO/segmentación + OCR
```

> Importante: Google Maps/Street View tiene restricciones de uso sobre contenido para entrenamiento, prueba o validación de modelos de IA. Por eso el MVP usa Google Maps/Places para **selección geográfica y datos de lugares**, y la fase visual debe conectarse a imágenes propias o a una fuente cuya licencia permita análisis automatizado.

## Requisitos de Google Cloud

Crea un proyecto en Google Cloud con facturación habilitada y activa:

- Maps JavaScript API
- Places API (New)

Usa **dos API keys** diferentes:

- `GOOGLE_MAPS_BROWSER_API_KEY`: restringida por HTTP referrer y habilitada solo para Maps JavaScript API.
- `GOOGLE_PLACES_API_KEY`: clave del backend, restringida a Places API (New) y, cuando despliegues, por IP.

Copia `.env.example` como `.env`:

```env
GOOGLE_MAPS_BROWSER_API_KEY=tu_clave_navegador
GOOGLE_PLACES_API_KEY=tu_clave_servidor
```

## Instalación

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

Inicia la aplicación:

```bash
uvicorn app:app --reload
```

Abre:

```text
http://127.0.0.1:8000
```

## Primera prueba recomendada

Empieza con **4–8 cuadras**, no con un barrio completo.

1. Haz clic en 4 o más esquinas del área.
2. Pulsa **Cerrar polígono**.
3. Usa inicialmente:
   - separación de barrido: `150 m`
   - radio Places: `120 m`
4. Pulsa **Analizar zona**.
5. Revisa los marcadores y descarga el CSV.

Una consulta Nearby Search devuelve como máximo 20 lugares por punto. Para un área comercial muy densa, reduce la separación/radio para aumentar cobertura, vigilando el costo de API.

## CSV generado

```text
place_id
nombre
direccion
latitud
longitud
tipo_principal
tipos
estado
website
google_maps_url
fachada_comercial
aviso_comercial
vitrina
nombre_ocr
confianza_vision
```

El archivo se guarda en `data/output/negocios_YYYYMMDD_HHMMSS.csv`.

## Fase 2: visión artificial

El repositorio conserva scripts experimentales de YOLO para imágenes que tengamos derecho a analizar. La siguiente integración agregará:

```text
imagen autorizada
   ↓
detector/segmentador
   ↓
fachada comercial? → aviso? → vitrina?
   ↓
OCR del aviso
   ↓
comparación nombre OCR vs Google Places
   ↓
tabla consolidada
```

### Etiquetas objetivo

- `fachada_comercial`
- `aviso_comercial`
- `vitrina`

Después podremos calcular una variable `oportunidad_web`, priorizando candidatos sin `websiteUri` y con evidencia visual de actividad comercial.

## Pruebas locales

```bash
pytest -q
```

## Documentación oficial usada

- Google Places API (New) — Nearby Search: https://developers.google.com/maps/documentation/places/web-service/nearby-search
- Google Maps JavaScript API: https://developers.google.com/maps/documentation/javascript
