import { init as initAgente } from './agente.js';

let agenteInitialized = false;

const VIEWS = {
    reconocimiento: 'view-reconocimiento',
    agente: 'view-agente',
};

function getElements() {
    return {
        tabRecon: document.getElementById('tab-reconocimiento'),
        tabAgente: document.getElementById('tab-agente'),
        viewRecon: document.getElementById('view-reconocimiento'),
        viewAgente: document.getElementById('view-agente'),
    };
}

function setActiveTab(active) {
    const { tabRecon, tabAgente } = getElements();
    if (active === 'reconocimiento') {
        tabRecon.classList.add('active');
        tabAgente.classList.remove('active');
    } else {
        tabAgente.classList.add('active');
        tabRecon.classList.remove('active');
    }
}

function showView(name) {
    const { viewRecon, viewAgente } = getElements();
    if (name === 'reconocimiento') {
        viewRecon.style.display = 'block';
        viewAgente.style.display = 'none';
    } else {
        viewRecon.style.display = 'none';
        viewAgente.style.display = 'block';

        if (!agenteInitialized) {
            initAgente();
            agenteInitialized = true;
        }
    }
}

export function init() {
    const { tabRecon, tabAgente } = getElements();

    // Default: Reconocimiento visible, Agente hidden
    showView('reconocimiento');
    setActiveTab('reconocimiento');

    tabRecon.onclick = () => {
        showView('reconocimiento');
        setActiveTab('reconocimiento');
    };

    tabAgente.onclick = () => {
        showView('agente');
        setActiveTab('agente');
    };
}
