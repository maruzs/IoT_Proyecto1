import { apiPost, formatTimestamp } from './api.js';

// Chat state
const messages = [];
let isLoading = false;

const QUERY_TIMEOUT_MS = 30000;

// ---------------------------------------------------------------------------
// Response text extraction — lightweight, LangGraph-replaceable
// ---------------------------------------------------------------------------
// Priority-ordered keys that likely hold the human-readable answer.
// When LangGraph takes over response formatting, replace this function.
const TEXT_KEYS = ['message', 'response_message', 'response', 'text', 'answer', 'content'];

function extractText(responseObj) {
    if (!responseObj || typeof responseObj !== 'object') return null;

    for (const key of TEXT_KEYS) {
        if (typeof responseObj[key] === 'string' && responseObj[key].trim()) {
            return responseObj[key];
        }
    }
    return null;
}

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
        const res = await fetch('/llm/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: text }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        clearLoading();

        if (!res.ok) {
            if (res.status >= 500) {
                renderError('Server error. Please try again later.');
            } else {
                renderError(`Error ${res.status}. Please try again.`);
            }
            setInputDisabled(false);
            getElements().input.focus();
            return;
        }

        const data = await res.json();

        // Extract human-readable text from the structured response.
        // Priority: parsed field → raw ollama text → stringify fallback.
        let responseText;
        if (data.response != null && typeof data.response === 'object') {
            responseText = extractText(data.response) || JSON.stringify(data.response);
        } else if (typeof data.response === 'string') {
            responseText = data.response;
        } else {
            responseText = data.raw || JSON.stringify(data);
        }

        messages.push({ sender: 'agent', text: responseText, timestamp: new Date().toISOString() });
        renderMessage(responseText, 'agent');
    } catch (err) {
        clearTimeout(timeoutId);
        clearLoading();

        if (err.name === 'AbortError') {
            renderError('Request timed out. Please try again.');
        } else {
            renderError('Network error. Check your connection.');
        }
    } finally {
        isLoading = false;
        setInputDisabled(false);
        getElements().input.focus();
    }
}

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
