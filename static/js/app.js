import { WebSocketClient } from './websocket.js';

const wsUrl = `ws://${window.location.host}/ws`;
const ws = new WebSocketClient(wsUrl);

// DOM Elements
const statusIndicator = document.getElementById('status-indicator');
const terminalOutput = document.getElementById('terminal-output');
const textInput = document.getElementById('text-input');
const micBtn = document.getElementById('mic-btn');
const sendBtn = document.getElementById('send-btn');
const clearLogsBtn = document.getElementById('clear-logs-btn');
const visionSelect = document.getElementById('vision-select');
const coreMemoryEditor = document.getElementById('core-memory-editor');
const saveMemoryBtn = document.getElementById('save-memory-btn');
const saveStatus = document.getElementById('save-status');

// ───────────────────── WebSocket Handling ─────────────────────
ws.on('connected', () => {
    statusIndicator.className = 'connected';
    appendLog('System', 'Connected to NeuroMango Server.', 'system');
});

ws.on('disconnected', () => {
    statusIndicator.className = 'disconnected';
    appendLog('System', 'Disconnected from server.', 'error');
});

// We only care about text events and thoughts for the dashboard
// Since Unity handles audio, we can ignore audio_data and visemes.
ws.on('speak_chunk', (data) => {
    appendLog('AI', data.text, 'system');
});

ws.on('thought', (data) => {
    appendLog('🧠 Thought', data.text, 'thought');
});

ws.on('system_log', (data) => {
    appendLog('System', data.text, 'system');
    if (data.text.includes('✅ Models loaded')) {
        textInput.disabled = false;
        sendBtn.disabled = false;
        textInput.placeholder = "Enter system command or chat message...";
    }
});

// Initially disable input until system is ready
textInput.disabled = true;
sendBtn.disabled = true;
textInput.placeholder = "System initializing, please wait...";

ws.connect();

// ───────────────────── Terminal Logic ─────────────────────
function appendLog(sender, text, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const time = new Date().toLocaleTimeString('ru-RU', { hour12: false });
    entry.innerHTML = `<span style="opacity:0.5">[${time}]</span> <strong>${sender}:</strong> ${text}`;
    
    terminalOutput.appendChild(entry);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

clearLogsBtn.addEventListener('click', () => {
    terminalOutput.innerHTML = '';
});

// ───────────────────── Chat Input ─────────────────────
function sendMessage() {
    const text = textInput.value.trim();
    if (!text) return;

    appendLog('Artem (You)', text, 'user');
    
    fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            text: text,
            sender_name: 'Артём',
            sender_role: 'developer'
        })
    }).catch(err => {
        appendLog('Error', 'Failed to send message: ' + err, 'error');
    });

    textInput.value = '';
}

sendBtn.addEventListener('click', sendMessage);
textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ───────────────────── Vision Controls ─────────────────────
visionSelect.addEventListener('change', async (e) => {
    const mode = e.target.value;
    try {
        const res = await fetch(`/api/vision/mode?mode=${mode}`, { method: 'POST' });
        const json = await res.json();
        if (json.status === "ok") {
            appendLog('System', `Vision mode set to: ${mode}`, 'system');
        }
    } catch (err) {
        appendLog('Error', 'Failed to set vision mode: ' + err, 'error');
    }
});

// ───────────────────── Module Controls ─────────────────────
const moduleButtons = document.querySelectorAll('.module-btn');

async function loadModules() {
    try {
        const res = await fetch('/api/modules');
        const modules = await res.json();
        updateModuleButtons(modules);
    } catch (err) {
        console.error('Failed to load modules:', err);
    }
}

function updateModuleButtons(modules) {
    moduleButtons.forEach(btn => {
        const modName = btn.dataset.module;
        if (modules[modName]) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

moduleButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
        const modName = btn.dataset.module;
        const isEnabled = btn.classList.contains('active');
        const newState = !isEnabled;
        
        try {
            const res = await fetch(`/api/modules/toggle?module=${modName}&enabled=${newState}`, { method: 'POST' });
            const json = await res.json();
            if (json.status === 'ok') {
                updateModuleButtons(json.modules);
                appendLog('System', `Module ${modName} set to: ${newState ? 'ON' : 'OFF'}`, 'system');
            }
        } catch (err) {
            appendLog('Error', `Failed to toggle ${modName}: ` + err, 'error');
        }
    });
});

// Remove old heartbeat_status listener since we now update UI instantly on toggle response
// but just in case other clients toggle it:
ws.on('heartbeat_status', (data) => {
    loadModules();
});

// Load modules state on startup
loadModules();

// ───────────────────── Core Memory Logic ─────────────────────
async function loadCoreMemory() {
    try {
        saveStatus.textContent = 'Loading...';
        const res = await fetch('/api/memory');
        const data = await res.json();
        if (data.text) {
            coreMemoryEditor.value = data.text;
            saveStatus.textContent = 'Loaded';
            saveStatus.style.color = 'var(--text-secondary)';
        } else {
            throw new Error(data.error || 'Failed to load');
        }
    } catch (err) {
        saveStatus.textContent = 'Error loading';
        saveStatus.style.color = 'var(--danger)';
        appendLog('Error', 'Could not load core memory: ' + err, 'error');
    }
}

async function saveCoreMemory() {
    const text = coreMemoryEditor.value;
    try {
        saveStatus.textContent = 'Saving...';
        saveMemoryBtn.disabled = true;
        
        const res = await fetch('/api/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        
        const data = await res.json();
        if (data.status === 'ok') {
            saveStatus.textContent = 'Saved!';
            saveStatus.style.color = 'var(--success)';
            appendLog('System', 'Core Memory successfully updated and reloaded by server.', 'system');
            
            setTimeout(() => {
                saveStatus.textContent = 'Ready';
                saveStatus.style.color = 'var(--text-secondary)';
            }, 3000);
        } else {
            throw new Error(data.error || 'Failed to save');
        }
    } catch (err) {
        saveStatus.textContent = 'Error saving';
        saveStatus.style.color = 'var(--danger)';
        appendLog('Error', 'Could not save core memory: ' + err, 'error');
    } finally {
        saveMemoryBtn.disabled = false;
    }
}

saveMemoryBtn.addEventListener('click', saveCoreMemory);

// Initial Load
loadCoreMemory();

// ───────────────────── Web Speech API (Client-side STT) ─────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    let isRecording = false;

    micBtn.addEventListener('click', () => {
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });

    recognition.addEventListener('start', () => {
        isRecording = true;
        micBtn.style.color = '#ef4444'; // Red when recording
        micBtn.classList.add('pulse');
        textInput.placeholder = "Listening...";
    });

    recognition.addEventListener('end', () => {
        isRecording = false;
        micBtn.style.color = '';
        micBtn.classList.remove('pulse');
        textInput.placeholder = "Enter system command or chat message...";
    });

    recognition.addEventListener('result', (event) => {
        const transcript = event.results[0][0].transcript;
        textInput.value = transcript;
        sendMessage(); // Automatically send when recognized
    });

    recognition.addEventListener('error', (event) => {
        console.error('Speech recognition error:', event.error);
        appendLog('System', `Speech recognition error: ${event.error}`, 'error');
    });

    // Web Speech API will only be triggered by the microphone button click.

} else {
    micBtn.style.display = 'none'; // Hide if browser doesn't support it
    appendLog('System', 'Web Speech API is not supported in this browser.', 'error');
}
