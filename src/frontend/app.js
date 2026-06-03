// State
let enrollmentDeadline = null;
let enrollmentInterval = null;
let lastEventId = null;

// Polling intervals (ms)
const POLL_EVENT = 2000;
const POLL_LOG = 5000;

// API helpers
async function apiGet(path) {
    try {
        const res = await fetch(path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`GET ${path} failed:`, err);
        return null;
    }
}

async function apiPost(path, body) {
    try {
        const res = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`POST ${path} failed:`, err);
        return null;
    }
}

// Format countdown as mm:ss
function fmtCountdown(msLeft) {
    if (msLeft <= 0) return '00:00';
    const totalSec = Math.ceil(msLeft / 1000);
    const mm = String(Math.floor(totalSec / 60)).padStart(2, '0');
    const ss = String(totalSec % 60).padStart(2, '0');
    return `${mm}:${ss}`;
}

function formatTimestamp(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

// Components
function updateDetectionCard() {
    apiGet('/api/ultimo-evento').then(data => {
        const statusEl = document.getElementById('detection-status');
        const userEl = document.getElementById('detection-user');
        const timeEl = document.getElementById('detection-time');

        if (!data || Object.keys(data).length === 0) {
            statusEl.textContent = 'Sin actividad';
            userEl.textContent = '';
            timeEl.textContent = '';
            return;
        }

        const evento = data.evento || 'Sin actividad';
        let statusText = 'Sin actividad';
        if (evento === 'Entrada Automática') statusText = 'Permitido';
        else if (evento === 'Desconocido Detectado') statusText = 'Denegado — rostro detectado';
        else if (evento === 'Sin Rostro') statusText = 'Sin rostro';
        else if (evento === 'Apertura Manual') statusText = 'Apertura Manual';

        statusEl.textContent = statusText;
        userEl.textContent = data.usuario || 'Desconocido';
        timeEl.textContent = formatTimestamp(data.timestamp);

        if (data.enrollable && data.id !== lastEventId) {
            lastEventId = data.id;
            showEnrollmentForm(data.enrollment_deadline);
        }
    });
}

function showEnrollmentForm(deadlineISO) {
    const section = document.getElementById('enrollment');
    const countdownEl = document.getElementById('enrollment-countdown');
    const nameInput = document.getElementById('enrollment-name');

    section.style.display = 'block';
    nameInput.value = '';
    countdownEl.textContent = '';
    enrollmentDeadline = new Date(deadlineISO).getTime();

    if (enrollmentInterval) clearInterval(enrollmentInterval);

    enrollmentInterval = setInterval(() => {
        const left = enrollmentDeadline - Date.now();
        countdownEl.textContent = `Tiempo restante: ${fmtCountdown(left)}`;
        if (left <= 0) hideEnrollmentForm();
    }, 1000);
}

function hideEnrollmentForm() {
    const section = document.getElementById('enrollment');
    section.style.display = 'none';
    if (enrollmentInterval) {
        clearInterval(enrollmentInterval);
        enrollmentInterval = null;
    }
    enrollmentDeadline = null;
}

async function handleEnrollSubmit() {
    const nameInput = document.getElementById('enrollment-name');
    const countdownEl = document.getElementById('enrollment-countdown');
    const name = nameInput.value.trim();

    if (!name) {
        countdownEl.textContent = 'Ingresá un nombre válido.';
        countdownEl.style.color = '#f87171';
        return;
    }

    const result = await apiPost('/api/enrolar', { nombre: name });
    if (result && result.id) {
        alert(`Enrolado correctamente: ${result.nombre}`);
        hideEnrollmentForm();
    } else {
        countdownEl.textContent = 'Error al enrolar. Verificá que la ventana no haya expirado.';
        countdownEl.style.color = '#f87171';
    }
}

async function handleCapture() {
    const btn = document.getElementById('btn-capture');
    btn.disabled = true;
    btn.textContent = 'Capturando...';

    const result = await apiPost('/api/capturar', {});
    btn.disabled = false;
    btn.textContent = 'Ver Imagen';

    if (!result) {
        alert('Error al capturar');
        return;
    }

    // Refresh the camera feed
    handleRefreshImage();

    // Update detection card immediately
    updateDetectionCard();
}
async function handleOpenDoor() {
    const result = await apiPost('/api/abrir-puerta', {});
    if (result && result.status === 'ok') {
        alert('Puerta abierta');
    } else {
        alert('No se pudo abrir la puerta');
    }
}

function handleRefreshImage() {
    const feed = document.getElementById('camera-feed');
    feed.src = '/api/stream?t=' + Date.now();
}

function updateAccessLog() {
    apiGet('/api/historial?limit=50').then(data => {
        const tbody = document.getElementById('log-body');
        if (!Array.isArray(data)) {
            tbody.innerHTML = '<tr><td colspan="3">Error cargando historial</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        data.forEach(entry => {
            const tr = document.createElement('tr');
            const user = entry.usuario || 'Desconocido';
            tr.innerHTML = `
                <td>${formatTimestamp(entry.timestamp)}</td>
                <td>${user}</td>
                <td>${entry.evento || ''}</td>
            `;
            tbody.appendChild(tr);
        });
    });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    setInterval(updateDetectionCard, POLL_EVENT);
    setInterval(updateAccessLog, POLL_LOG);
    document.getElementById('btn-open-door').onclick = handleOpenDoor;
    document.getElementById('btn-capture').onclick = handleCapture;
    document.getElementById('enrollment-submit').onclick = handleEnrollSubmit;

    // Initial load
    updateDetectionCard();
    updateAccessLog();
});

// Cleanup on unload
window.addEventListener('beforeunload', () => {
    if (enrollmentInterval) clearInterval(enrollmentInterval);
});
