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

    const point = {
      lat: event.latLng.lat(),
      lng: event.latLng.lng(),
    };

    polygonPath.push(point);

    const marker = new google.maps.Marker({
      position: point,
      map,
      label: String(polygonPath.length),
    });

    vertexMarkers.push(marker);
    renderPolygon();
    updateStatus();
    resetEstimate();
  });
};

function getMode() {
  return document.querySelector('input[name="analysisMode"]:checked').value;
}

function modeLabel(mode) {
  return {
    count: 'Solo conteo',
    economic: 'Análisis económico',
    complete: 'Análisis completo',
  }[mode] || mode;
}

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
  const status = document.getElementById('status');

  status.textContent =
    message ||
    `${polygonPath.length} vértices seleccionados${polygonClosed ? ' · polígono cerrado' : ''}`;

  document.getElementById('estimate').disabled = !polygonClosed;
  document.getElementById('analyze').disabled = !polygonClosed;
}

function resetEstimate() {
  document.getElementById('estimateCard').classList.add('hidden');
}

document.querySelectorAll('input[name="analysisMode"]').forEach(input => {
  input.addEventListener('change', resetEstimate);
});

document.getElementById('closePolygon').addEventListener('click', () => {
  if (polygonPath.length < 3) {
    return updateStatus('Necesitas mínimo 3 puntos.');
  }

  polygonClosed = true;
  renderPolygon();
  updateStatus();
  resetEstimate();
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
  resetEstimate();
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

  resetEstimate();
  updateStatus('Esperando polígono…');
}

document.getElementById('estimate').addEventListener('click', async () => {
  if (!polygonClosed) return;

  const button = document.getElementById('estimate');
  button.disabled = true;
  updateStatus('Estimando comercios dentro del perímetro…');

  try {
    const mode = getMode();

    const response = await fetch('/api/estimate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        polygon: polygonPath,
        mode,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'No fue posible estimar la zona');
    }

    document.getElementById('estimateCount').textContent =
      Number(data.count).toLocaleString('es-CO');
    document.getElementById('estimateMode').textContent = modeLabel(data.mode);
    document.getElementById('estimateDetails').textContent =
      Number(data.estimated_detail_calls).toLocaleString('es-CO');
    document.getElementById('estimateCost').textContent = data.cost_level;
    document.getElementById('estimateNote').textContent = data.note;
    document.getElementById('estimateCard').classList.remove('hidden');

    updateStatus(`Estimación lista: ${data.count} comercios.`);
  } catch (err) {
    updateStatus(`Error: ${err.message}`);
  } finally {
    button.disabled = !polygonClosed;
  }
});

document.getElementById('analyze').addEventListener('click', async () => {
  if (!polygonClosed) return;

  const button = document.getElementById('analyze');
  button.disabled = true;

  const mode = getMode();
  updateStatus(`Ejecutando ${modeLabel(mode).toLowerCase()}…`);

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        polygon: polygonPath,
        mode,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Error al analizar la zona');
    }

    renderResults(data);

    if (mode === 'count') {
      updateStatus(`Conteo listo: ${data.count} comercios estimados.`);
    } else {
      updateStatus(`Listo: ${data.count} comercios encontrados.`);
    }
  } catch (err) {
    updateStatus(`Error: ${err.message}`);
  } finally {
    button.disabled = !polygonClosed;
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

  if (data.mode === 'count') {
    document.getElementById('summary').textContent =
      `${data.count} comercios estimados en el perímetro. No se solicitaron detalles individuales.`;

    document.getElementById('downloadCsv').classList.add('hidden');
    return;
  }

  data.places.forEach((place, index) => {
    if (place.latitud != null && place.longitud != null) {
      const marker = new google.maps.Marker({
        position: {
          lat: Number(place.latitud),
          lng: Number(place.longitud),
        },
        map,
        label: String(index + 1),
        title: place.nombre,
      });

      resultMarkers.push(marker);
    }

    const webCell = data.mode === 'complete'
      ? (place.website
          ? `<a href="${escapeAttr(place.website)}" target="_blank" rel="noopener">Sí</a>`
          : '<strong>No</strong>')
      : '<span class="muted">No consultado</span>';

    const row = document.createElement('tr');

    row.innerHTML = `
      <td>${escapeHtml(place.nombre)}</td>
      <td>${escapeHtml(place.direccion)}</td>
      <td>${escapeHtml(place.tipo_principal || '')}</td>
      <td>${webCell}</td>
      <td>${place.google_maps_url ? `<a href="${escapeAttr(place.google_maps_url)}" target="_blank" rel="noopener">Abrir</a>` : ''}</td>
      <td>${escapeHtml(place.fachada_comercial)}</td>
    `;

    tbody.appendChild(row);
  });

  document.getElementById('summary').textContent =
    `${data.count} comercios · modo: ${modeLabel(data.mode)} · ${data.place_ids.length} Place IDs disponibles.`;

  const download = document.getElementById('downloadCsv');

  if (data.id_file) {
    download.href = `/api/download/${encodeURIComponent(data.id_file)}`;
    download.classList.remove('hidden');
  } else {
    download.classList.add('hidden');
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(
    /[&<>'"]/g,
    char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;',
    })[char]
  );
}

function escapeAttr(value) {
  return escapeHtml(value);
}

bootstrap();
