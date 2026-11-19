let map;
let polygonPath = [];
let polygonShape = null;
let vertexMarkers = [];
let resultMarkers = [];
let gridMarkers = [];
let polygonClosed = false;

async function bootstrap() {
  const cfg = await fetch('/api/config').then(r => r.json());
  if (!cfg.googleMapsBrowserApiKey) {
    document.getElementById('status').textContent =
      'Falta GOOGLE_MAPS_BROWSER_API_KEY en .env';
    return;
  }

  const script = document.createElement('script');
  script.src =
    `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(cfg.googleMapsBrowserApiKey)}&callback=initMap&loading=async`;
  script.async = true;
  window.__mapConfig = cfg;
  document.head.appendChild(script);
}

window.initMap = function initMap() {
  const cfg = window.__mapConfig;
  map = new google.maps.Map(document.getElementById('map'), {
    center: cfg.defaultCenter,
    zoom: cfg.defaultZoom,
    mapTypeControl: true,
    streetViewControl: false,
  });

  map.addListener('click', event => {
    if (polygonClosed) return;
    const p = { lat: event.latLng.lat(), lng: event.latLng.lng() };
    polygonPath.push(p);
    const marker = new google.maps.Marker({
      position: p,
      map,
      label: String(polygonPath.length),
    });
    vertexMarkers.push(marker);
    renderDraftPolygon();
    updateStatus();
  });
};

function renderDraftPolygon() {
  if (polygonShape) polygonShape.setMap(null);
  if (polygonPath.length < 2) return;

  polygonShape = new google.maps.Polygon({
    paths: polygonPath,
    strokeOpacity: 0.9,
    strokeWeight: 2,
    fillOpacity: polygonClosed ? 0.18 : 0.05,
    map,
  });
}

function updateStatus(message) {
  const el = document.getElementById('status');
  el.textContent =
    message ||
    `${polygonPath.length} vértices seleccionados${polygonClosed ? ' · polígono cerrado' : ''}`;
  document.getElementById('analyze').disabled = !polygonClosed;
}

document.getElementById('closePolygon').addEventListener('click', () => {
  if (polygonPath.length < 3) {
    return updateStatus('Necesitas mínimo 3 puntos.');
  }
  polygonClosed = true;
  renderDraftPolygon();
  updateStatus();
});

document.getElementById('undoPoint').addEventListener('click', () => {
  if (polygonClosed) {
    return updateStatus('Primero limpia el polígono para volver a editarlo.');
  }
  polygonPath.pop();
  const marker = vertexMarkers.pop();
  if (marker) marker.setMap(null);
  renderDraftPolygon();
  updateStatus();
});

document.getElementById('clearMap').addEventListener('click', clearAll);

function clearAll() {
  polygonClosed = false;
  polygonPath = [];
  if (polygonShape) polygonShape.setMap(null);
  polygonShape = null;

  [...vertexMarkers, ...resultMarkers, ...gridMarkers].forEach(m => m.setMap(null));
  vertexMarkers = [];
  resultMarkers = [];
  gridMarkers = [];

  document.getElementById('resultsBody').innerHTML = '';
  document.getElementById('summary').textContent = 'Aún no hay resultados.';
  document.getElementById('downloadCsv').classList.add('hidden');
  updateStatus('Esperando polígono…');
}

document.getElementById('analyze').addEventListener('click', async () => {
  if (!polygonClosed) return;

  updateStatus('Consultando Google Places…');
  document.getElementById('analyze').disabled = true;

  const payload = {
    polygon: polygonPath,
    grid_spacing_m: Number(document.getElementById('gridSpacing').value),
    search_radius_m: Number(document.getElementById('searchRadius').value),
    max_grid_points: 120,
  };

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Error al analizar la zona');
    }

    renderResults(data);
    updateStatus(`Listo: ${data.count} negocios candidatos.`);
  } catch (err) {
    updateStatus(`Error: ${err.message}`);
  } finally {
    document.getElementById('analyze').disabled = false;
  }
});

function renderResults(data) {
  [...resultMarkers, ...gridMarkers].forEach(m => m.setMap(null));
  resultMarkers = [];
  gridMarkers = [];

  data.grid_points.forEach(p => {
    gridMarkers.push(
      new google.maps.Marker({
        position: p,
        map,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 3,
          fillOpacity: 0.5,
          strokeWeight: 1,
        },
        title: 'Punto de barrido',
      })
    );
  });

  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = '';

  data.places.forEach((place, idx) => {
    const marker = new google.maps.Marker({
      position: {
        lat: Number(place.latitud),
        lng: Number(place.longitud),
      },
      map,
      label: String(idx + 1),
      title: place.nombre,
    });
    resultMarkers.push(marker);

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(place.nombre)}</td>
      <td>${escapeHtml(place.direccion)}</td>
      <td>${escapeHtml(place.tipo_principal || '')}</td>
      <td>${place.website ? `<a href="${escapeAttr(place.website)}" target="_blank">Sí</a>` : '<strong>No</strong>'}</td>
      <td>${place.google_maps_url ? `<a href="${escapeAttr(place.google_maps_url)}" target="_blank">Abrir</a>` : ''}</td>
      <td>${escapeHtml(place.fachada_comercial)}</td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById('summary').textContent =
    `${data.count} candidatos · ${data.grid_points.length} puntos de barrido.`;

  const a = document.getElementById('downloadCsv');
  a.href = `/api/download/${encodeURIComponent(data.csv_file)}`;
  a.classList.remove('hidden');
}

function escapeHtml(value) {
  return String(value ?? '').replace(
    /[&<>'"]/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[c]
  );
}

function escapeAttr(value) {
  return escapeHtml(value);
}

bootstrap();
