import { init as initNav } from './modules/nav.js';
import { init as initReconocimiento, destroy as destroyReconocimiento } from './modules/reconocimiento.js';

document.addEventListener('DOMContentLoaded', () => {
    initNav();
    initReconocimiento();
});

window.addEventListener('beforeunload', () => {
    destroyReconocimiento();
});
