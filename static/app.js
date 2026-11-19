let map;
let polygonPath = [];
let polygonShape = null;
let vertexMarkers = [];
let resultMarkers = [];
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

    renderPolygon();
    updateStatus();
  });
};

function renderPolygon() {
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
  renderPolygon();
  updateStatus();
});

document.getElementById('undoPoint').addEventListener('click', () => {
  if (polygonClosed) {
    return updateStatus('Primero limpia el polígono para volver a editarlo.');
  }

  polygonPath.pop();
  const marker = vertexMarkers.pop();
  if (marker) marker.setMap(null);

  renderPolygon();
  updateStatus();
});

document.getElementById('clearMap').addEventListener('click', clearAll);

function clearAll() {
  polygonClosed = false;
  polygonPath = [];

  if (polygonShape) polygonShape.setMap(null);
  polygonShape = null;

  [...vertexMarkers, ...resultMarkers].forEach(marker => marker.setMap(null));
  vertexMarkers = [];
  resultMarkers = [];

  document.getElementById('resultsBody').innerHTML = '';
  document.getElementById('summary').textContent = 'Aún no hay resultados.';
  document.getElementById('warning').classList.add('hidden');
  document.getElementById('downloadCsv').classList.add('hidden');

  updateStatus('Esperando polígono…');
}

document.getElementById('analyze').addEventListener('click', async () => {
  if (!polygonClosed) return;

  updateStatus('Consultando comercios dentro del perímetro…');
  document.getElementById('analyze').disabled = true;

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ polygon: polygonPath }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Error al analizar la zona');
    }

    renderResults(data);
    updateStatus(`Listo: ${data.count} comercios encontrados.`);
  } catch (err) {
    updateStatus(`Error: ${err.message}`);
  } finally {
    document.getElementById('analyze').disabled = false;
  }
});

function renderResults(data) {
  resultMarkers.forEach(marker => marker.setMap(null));
  resultMarkers = [];

  const warning = document.getElementById('warning');
  if (data.warning) {
    warning.textContent = data.warning;
    warning.classList.remove('hidden');
  } else {
    warning.classList.add('hidden');
  }

  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = '';

  data.places.forEach((place, idx) => {
    if (place.latitud != null && place.longitud != null) {
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
    }

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
    `${data.count} comercios en el perímetro · ${data.place_ids.length} Place IDs disponibles.`;

  const a = document.getElementById('downloadCsv');
  if (data.id_file) {
    a.href = `/api/download/${encodeURIComponent(data.id_file)}`;
    a.classList.remove('hidden');
  } else {
    a.classList.add('hidden');
  }
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
