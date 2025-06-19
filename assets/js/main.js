// --- CONFIGURAÇÃO DO BACKEND ---
const BACKEND_URL = 'https://narrador-python-api-1.onrender.com';  // URL do seu serviço no Render

// --- ELEMENTOS DO DOM ---
const mainArea = document.getElementById('main-component-area');

let selectedVoice = null;
let selectedFormat = 'padrao';
let selectedStyle = 'padrao';
let selectedSpeed = '2';

// --- CARREGAMENTO INICIAL ---
document.addEventListener('DOMContentLoaded', () => {
    renderVoiceGrid();
    renderControls();
});

// --- INTERFACE - LISTA DE LOCUTORES ---
function renderVoiceGrid() {
    const container = document.createElement('div');
    container.className = 'voice-grid';
    container.style.display = 'flex';
    container.style.flexWrap = 'wrap';
    container.style.justifyContent = 'center';

    voices.forEach(voice => {
        const card = createVoiceCard(voice);
        container.appendChild(card);
    });

    mainArea.appendChild(container);
}

function createVoiceCard(voice) {
    const card = document.createElement('div');
    card.className = 'voice-card';
    card.dataset.id = voice.id;

    card.innerHTML = `
        <img src="${voice.imageUrl}" alt="${voice.name}">
        <div class="voice-name">${voice.name}</div>
        <div class="voice-specialty">${voice.specialty}</div>
    `;

    card.addEventListener('click', () => {
        document.querySelectorAll('.voice-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedVoice = voice.id;
    });

    return card;
}

// --- CONTROLES DE GERAÇÃO DE ÁUDIO ---
function renderControls() {
    const container = document.createElement('div');
    container.style.marginTop = '32px';
    container.style.textAlign = 'center';

    container.innerHTML = `
        <div style="margin-bottom: 16px;">
            <label for="formatSelect">Formato:</label>
            <select id="formatSelect" style="padding: 8px; border-radius: 8px; border: none;"></select>
        </div>

        <div style="margin-bottom: 16px;">
            <label for="styleSelect">Estilo:</label>
            <select id="styleSelect" style="padding: 8px; border-radius: 8px; border: none;"></select>
        </div>

        <div style="margin-bottom: 16px;">
            <label for="speedSelect">Velocidade:</label>
            <select id="speedSelect" style="padding: 8px; border-radius: 8px; border: none;"></select>
        </div>

        <div style="margin-bottom: 16px;">
            <textarea id="textInput" rows="5" placeholder="Digite aqui o texto a ser narrado..." style="width: 90%; max-width: 600px; padding: 12px; font-size: 1rem; border-radius: 12px; border: none;"></textarea>
        </div>

        <button id="generateBtn" style="padding: 12px 24px; font-size: 1rem; border-radius: 12px; background-color: #36eaff; color: #000; border: none; cursor: pointer;">Gerar Narração</button>

        <div id="audioPlayer" style="margin-top: 24px;"></div>
    `;

    mainArea.appendChild(container);

    populateSelect('formatSelect', formatOptions, selectedFormat);
    populateSelect('styleSelect', styleOptions, selectedStyle);
    populateSelect('speedSelect', speedOptions, selectedSpeed);

    document.getElementById('generateBtn').addEventListener('click', handleGenerateAudio);

    document.getElementById('formatSelect').addEventListener('change', (e) => {
        selectedFormat = e.target.value;
        updateStyleBasedOnFormat(selectedFormat);
    });
}

// --- PREENCHE SELECTS DINAMICAMENTE ---
function populateSelect(id, options, selectedValue) {
    const select = document.getElementById(id);
    options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.text;
        if (option.value === selectedValue) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
}

// --- ATUALIZAÇÃO DE ESTILO BASEADO NO FORMATO SELECIONADO ---
function updateStyleBasedOnFormat(format) {
    const styleSelect = document.getElementById('styleSelect');
    const currentPrompt = prompts[format] || {};
    const newOptions = Object.keys(currentPrompt).map(key => ({
        value: key,
        text: styleOptions.find(s => s.value === key)?.text || key
    }));

    styleSelect.innerHTML = '';
    newOptions.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.text;
        styleSelect.appendChild(opt);
    });

    selectedStyle = newOptions[0]?.value || 'padrao';
    styleSelect.value = selectedStyle;
}

// --- ENVIA REQUISIÇÃO AO BACKEND ---
function handleGenerateAudio() {
    const textInput = document.getElementById('textInput').value.trim();
    const format = document.getElementById('formatSelect').value;
    const style = document.getElementById('styleSelect').value;
    const speed = document.getElementById('speedSelect').value;

    if (!textInput) {
        alert('Por favor, digite um texto.');
        return;
    }

    if (!selectedVoice) {
        alert('Selecione uma voz antes de continuar.');
        return;
    }

    const promptText = prompts[format][style];
    const speedText = speedPrompts[speed];

    const fullPrompt = `${promptText} ${speedText} "${textInput}"`;

    const audioPlayerDiv = document.getElementById('audioPlayer');
    audioPlayerDiv.innerHTML = '<p>Gerando áudio... por favor aguarde.</p>';

    fetch(`${BACKEND_URL}/generate-audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: fullPrompt,
            voice: selectedVoice,
            style: promptText
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }

        const audioUrl = `data:audio/wav;base64,${data.audio_data}`;

        audioPlayerDiv.innerHTML = `
            <audio controls style="width: 100%; max-width: 600px;">
                <source src="${audioUrl}" type="audio/wav">
                Seu navegador não suporta o elemento de áudio.
            </audio>
        `;
    })
    .catch(error => {
        console.error('Erro ao gerar áudio:', error);
        audioPlayerDiv.innerHTML = `<p style="color: red;">Erro ao gerar áudio: ${error.message}</p>`;
    });
}