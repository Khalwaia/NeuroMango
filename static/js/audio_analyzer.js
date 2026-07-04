/**
 * NeuroMango — Client-Side Audio Analyzer
 * Plays audio received from the server and performs real-time FFT analysis
 * to extract viseme weights for lip sync. All analysis happens in the browser
 * so visemes are perfectly synchronized with audio playback.
 */

export class AudioAnalyzer {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.currentSource = null;
        this.frequencyData = null;
        this._isPlaying = false;
        this._onEndedCallback = null;
    }

    /** Ensure AudioContext is created and resumed (call on user gesture). */
    async ensureContext() {
        if (!this.audioContext) {
            this.audioContext = new AudioContext();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.5;
            this.analyser.minDecibels = -90;
            this.analyser.maxDecibels = -10;
            this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
        }
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    /**
     * Decode and play audio from an ArrayBuffer (MP3/WAV/OGG).
     * @param {ArrayBuffer} audioBuffer — raw audio file bytes
     * @param {function} onEnded — callback when playback finishes
     */
    async playAudio(audioBuffer, onEnded) {
        await this.ensureContext();
        this.stop(); // Stop any previous playback

        try {
            const decodedBuffer = await this.audioContext.decodeAudioData(audioBuffer);

            const source = this.audioContext.createBufferSource();
            source.buffer = decodedBuffer;

            // Route: source → analyser → destination (speakers)
            source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);

            source.start();
            this.currentSource = source;
            this._isPlaying = true;
            this._onEndedCallback = onEnded;

            source.onended = () => {
                this._isPlaying = false;
                this.currentSource = null;
                if (this._onEndedCallback) {
                    this._onEndedCallback();
                }
            };

            console.log(`[Audio] Playing: ${decodedBuffer.duration.toFixed(1)}s, ${decodedBuffer.sampleRate}Hz`);
        } catch (err) {
            console.error('[Audio] Decode/playback error:', err);
            this._isPlaying = false;
        }
    }

    /** Stop current playback. */
    stop() {
        if (this.currentSource) {
            try { this.currentSource.stop(); } catch (e) { /* already stopped */ }
            this.currentSource = null;
        }
        this._isPlaying = false;
        // Disconnect analyser from destination to prevent double-connections
        if (this.analyser) {
            try { this.analyser.disconnect(); } catch (e) {}
        }
    }

    /** @returns {boolean} Whether audio is currently playing. */
    isPlaying() {
        return this._isPlaying;
    }

    /**
     * Analyze current audio frame and return VRM viseme weights.
     * Call this every animation frame.
     * @returns {object|null} Viseme weights {aa, ih, ou, ee, oh} or null if not playing
     */
    getVisemes() {
        if (!this._isPlaying || !this.analyser || !this.frequencyData) return null;

        this.analyser.getByteFrequencyData(this.frequencyData);

        const sampleRate = this.audioContext.sampleRate;
        const binWidth = sampleRate / this.analyser.fftSize;

        // Average energy in a frequency band (0–1)
        const bandEnergy = (lowHz, highHz) => {
            const lo = Math.max(0, Math.floor(lowHz / binWidth));
            const hi = Math.min(this.frequencyData.length - 1, Math.ceil(highHz / binWidth));
            if (hi <= lo) return 0;
            let sum = 0;
            for (let i = lo; i <= hi; i++) sum += this.frequencyData[i];
            return sum / (hi - lo + 1) / 255;  // normalize to 0–1
        };

        const eLow  = bandEnergy(100,  400);   // O, U — rounded vowels
        const eMid  = bandEnergy(400,  900);   // A — open mouth
        const eHigh = bandEnergy(900,  2500);  // I, E — narrow/smile
        const eAll  = bandEnergy(80,   3000);  // Overall speech energy

        // Mouth openness — scaled from overall energy
        const mouthOpen = Math.min(1.0, eAll * 3.0);

        if (mouthOpen < 0.04) {
            return { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 };
        }

        const total = eLow + eMid + eHigh + 0.001;

        return {
            aa: Math.min(1, (eMid  / total) * mouthOpen * 1.3),
            ih: Math.min(1, (eHigh / total) * mouthOpen * 0.6),
            ou: Math.min(1, (eLow  / total) * mouthOpen * 0.8),
            ee: Math.min(1, (eHigh / total) * mouthOpen * 0.55),
            oh: Math.min(1, (eLow  / total) * mouthOpen * 0.7),
        };
    }
}
