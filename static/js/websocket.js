/**
 * NeuroMango — WebSocket Client
 * Handles real-time communication with the Python backend.
 * Supports both JSON (text) and binary (audio) messages.
 */

export class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 10000;
        this.handlers = new Map();
        this._shouldReconnect = true;
        this._expectingAudio = false;
    }

    /**
     * Register a handler for a specific message type.
     * @param {string} type - Message type (e.g., 'viseme', 'speak_start', 'audio_data')
     * @param {function} handler - Callback function
     */
    on(type, handler) {
        if (!this.handlers.has(type)) {
            this.handlers.set(type, []);
        }
        this.handlers.get(type).push(handler);
    }

    /** Connect to the WebSocket server. */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

        this.ws = new WebSocket(this.url);
        this.ws.binaryType = 'arraybuffer';  // Receive binary as ArrayBuffer

        this.ws.onopen = () => {
            console.log('[WS] Connected');
            this.reconnectDelay = 1000;
            this._emit('connected', {});
        };

        this.ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                // JSON text message
                try {
                    const data = JSON.parse(event.data);

                    // If we receive speak_start, next binary message will be audio
                    if (data.type === 'speak_start') {
                        this._expectingAudio = true;
                    }

                    this._emit(data.type, data);
                } catch (e) {
                    console.warn('[WS] Failed to parse JSON message:', e);
                }
            } else if (event.data instanceof ArrayBuffer) {
                // Binary message — audio data
                if (this._expectingAudio) {
                    this._expectingAudio = false;
                    console.log(`[WS] Received audio: ${event.data.byteLength} bytes`);
                    this._emit('audio_data', { buffer: event.data });
                } else {
                    console.warn('[WS] Unexpected binary message');
                }
            }
        };

        this.ws.onclose = () => {
            console.log('[WS] Disconnected');
            this._emit('disconnected', {});
            if (this._shouldReconnect) {
                this._scheduleReconnect();
            }
        };

        this.ws.onerror = (err) => {
            console.error('[WS] Error:', err);
        };
    }

    /** Send JSON data to the server. */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    /** Send text for speech synthesis. */
    speak(text) {
        this.send({ type: 'speak', text });
    }

    /** Disconnect permanently. */
    disconnect() {
        this._shouldReconnect = false;
        if (this.ws) this.ws.close();
    }

    /** @private */
    _emit(type, data) {
        const handlers = this.handlers.get(type) || [];
        for (const handler of handlers) {
            try {
                handler(data);
            } catch (e) {
                console.error(`[WS] Handler error for '${type}':`, e);
            }
        }
    }

    /** @private */
    _scheduleReconnect() {
        console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms...`);
        setTimeout(() => {
            this.connect();
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
        }, this.reconnectDelay);
    }
}
