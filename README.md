# Fachadas Google Maps — piloto comercial

MVP para seleccionar un **perímetro sobre Google Maps**, identificar comercios dentro de ese polígono y preparar una segunda etapa de visión artificial para detectar fachada, aviso comercial, vitrina y texto del negocio.

## Qué hace hoy

1. Abre Google Maps en el navegador.
2. Permite marcar un polígono haciendo clic en sus vértices.
3. Envía ese polígono a **Places Aggregate API**.
4. Obtiene los Place IDs de comercios operativos dentro del área.
5. Consulta detalles en vivo para mostrarlos sobre Google Maps:
   - nombre
   - dirección
   - tipo
   - sitio web
   - enlace a Google Maps
6. Guarda de forma persistente solamente los **Place IDs**.

## Por qué se separa la persistencia

Las políticas de Google Maps Platform permiten almacenar Place IDs, pero restringen guardar/exportar contenido de Google Maps como nombres y direcciones de negocios. También restringen usar contenido de Street View para entrenar, probar, validar o ajustar modelos de IA.

Por eso la arquitectura final separa:

```text
GOOGLE MAPS / PLACES
selección geográfica + consulta/validación en vivo
              ↓
        Place IDs persistentes
              ↓
FUENTE DE IMÁGENES AUTORIZADA
              ↓
visión artificial + OCR
              ↓
TABLA PROPIA PERSISTENTE
nombre OCR + coordenadas propias + dirección de fuente abierta
```

## Requisitos de Google Cloud

Activa:

- Maps JavaScript API
- Places API (New)
- Places Aggregate API

Usa dos API keys:

- `GOOGLE_MAPS_BROWSER_API_KEY`: navegador, restringida por HTTP referrer.
- `GOOGLE_PLACES_API_KEY`: backend, restringida a Places API (New) y Places Aggregate API.

Copia `.env.example` a `.env`:

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
pip install -r requirements.txt
uvicorn app:app --reload
```

Abre:

```text
http://127.0.0.1:8000
```

## Primera prueba

Empieza con **4–8 cuadras**.

1. Haz clic en las esquinas del área.
2. Pulsa **Cerrar polígono**.
3. Pulsa **Analizar zona**.
4. Revisa los comercios encontrados.
5. Si aparecen más de 100, reduce el perímetro.
6. Descarga el CSV de Place IDs.

Places Aggregate API admite polígonos personalizados. Para `INSIGHT_PLACES`, Google devuelve Place IDs cuando el resultado es de 100 lugares o menos.

## Fase visual

La tabla final que buscamos será:

```text
id
latitud_propia
longitud_propia
direccion_fuente_abierta
fachada_comercial
aviso_comercial
vitrina
nombre_ocr
place_id_google
website_en_google_en_vivo
confianza_vision
```

La detección visual debe ejecutarse sobre imágenes que tengamos derecho a analizar, por ejemplo:

- fotografías propias;
- recorrido capturado con cámara/vehículo;
- una fuente abierta/licenciada para análisis automatizado.

### Clases iniciales

- `fachada_comercial`
- `aviso_comercial`
- `vitrina`

## Pruebas

```bash
pytest -q
```

## Referencias oficiales

- Places Aggregate API: https://developers.google.com/maps/documentation/places-aggregate
- Custom polygons: https://developers.google.com/maps/documentation/places-aggregate/request-parameters
- Places API policies: https://developers.google.com/maps/documentation/places/web-service/policies
- Google Maps Platform terms: https://cloud.google.com/terms/maps-platform
