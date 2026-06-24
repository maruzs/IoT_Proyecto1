import { apiPost, formatTimestamp } from './api.js';

// Chat state
const messages = [];
let isLoading = false;
let isWaitingConfirmation = false;

const QUERY_TIMEOUT_MS = 30000;

// ---------------------------------------------------------------------------
// Response formatting — structured AgentResponse from LangGraph
// ---------------------------------------------------------------------------

function formatAgentResponse(data) {
    // data = { status, decision?, state?, notification?, needs_confirmation? }

    // Pending clarification
    if (data.needs_confirmation) {
        isWaitingConfirmation = true;
        return data.notification?.razonamiento
            || "¿Confirmás esta acción? Responde sí o no.";
    }

    isWaitingConfirmation = false;

    // Normal decision — show reasoning
    if (data.decision) {
        const d = data.decision;
        const nivel = d.nivel ? `[${d.nivel.toUpperCase()}] ` : '';
        const razon = d.razonamiento || '';
        const acciones = d.acciones?.length
            ? `\n\nAcciones: ${d.acciones.map(a => a.tool).join(', ')}`
            : '';
        return `${nivel}${razon}${acciones}`;
    }

    // Fallback: raw notification text
    if (data.notification?.razonamiento) {
        return data.notification.razonamiento;
    }

    // State-only response (e.g. silenced mode change)
    if (data.state) {
        return `Modo: ${data.state.mode}. `
            + (data.state.mcp_connected ? 'Sensores conectados.' : 'Sensores desconectados.');
    }

    return 'Sin respuesta del agente.';
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function getElements() {
    return {
        msgList: document.getElementById('chat-messages'),
        input: document.getElementById('chat-input'),
        sendBtn: document.getElementById('chat-send'),
    };
}

function scrollToBottom() {
    const { msgList } = getElements();
    if (msgList) msgList.scrollTop = msgList.scrollHeight;
}

function renderMessage(text, sender, ts) {
    const { msgList } = getElements();
    if (!msgList) return;

    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${sender === 'user' ? 'msg-user' : 'msg-agent'}`;

    const textEl = document.createElement('div');
    textEl.className = 'msg-text';
    textEl.textContent = text;

    const metaEl = document.createElement('div');
    metaEl.className = 'msg-meta';
    metaEl.textContent = formatTimestamp(ts) || formatTimestamp(new Date().toISOString());

    bubble.appendChild(textEl);
    bubble.appendChild(metaEl);
    msgList.appendChild(bubble);
    scrollToBottom();
}

function renderLoading() {
    const { msgList } = getElements();
    if (!msgList) return;

    const existing = document.getElementById('chat-loading');
    if (existing) return;

    const bubble = document.createElement('div');
    bubble.id = 'chat-loading';
    bubble.className = 'msg-bubble msg-agent loading-dots';
    bubble.innerHTML = '<span></span><span></span><span></span>';
    msgList.appendChild(bubble);
    scrollToBottom();
}

function clearLoading() {
    const loading = document.getElementById('chat-loading');
    if (loading) loading.remove();
}

function renderError(text) {
    const { msgList } = getElements();
    if (!msgList) return;

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble msg-error';
    bubble.textContent = text;
    msgList.appendChild(bubble);
    scrollToBottom();
}

function setInputDisabled(disabled) {
    const { input, sendBtn } = getElements();
    if (input) input.disabled = disabled;
    if (sendBtn) sendBtn.disabled = disabled;
}

// ---------------------------------------------------------------------------
// Send message to LangGraph agent
// ---------------------------------------------------------------------------

export async function sendMessage() {
    if (isLoading) return;

    const { input } = getElements();
    const text = input.value.trim();

    if (!text) return;

    // User message
    messages.push({ sender: 'user', text, timestamp: new Date().toISOString() });
    renderMessage(text, 'user');
    input.value = '';

    // Loading state
    isLoading = true;
    setInputDisabled(true);
    renderLoading();

    // Abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS);

    try {
        const res = await fetch('/llm/agent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        clearLoading();

        if (!res.ok) {
            if (res.status >= 500) {
                renderError('Error del servidor. Probá de nuevo.');
            } else if (res.status === 504) {
                renderError('El agente tardó demasiado. Probá con un mensaje más corto.');
            } else {
                renderError(`Error ${res.status}. Probá de nuevo.`);
            }
            setInputDisabled(false);
            getElements().input.focus();
            return;
        }

        const data = await res.json();

        // Format the structured response for display
        const responseText = formatAgentResponse(data);

        messages.push({ sender: 'agent', text: responseText, timestamp: new Date().toISOString() });
        renderMessage(responseText, 'agent');

        // If waiting confirmation, show subtle hint
        if (data.needs_confirmation) {
            renderMessage('(Responde "sí" o "no")', 'agent');
        }
    } catch (err) {
        clearTimeout(timeoutId);
        clearLoading();

        if (err.name === 'AbortError') {
            renderError('Timeout. El agente no respondió a tiempo.');
        } else {
            renderError('Error de red. Revisá tu conexión.');
        }
    } finally {
        isLoading = false;
        setInputDisabled(false);
        getElements().input.focus();
    }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

export function init() {
    const { input, sendBtn } = getElements();

    if (sendBtn) {
        sendBtn.onclick = sendMessage;
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}
