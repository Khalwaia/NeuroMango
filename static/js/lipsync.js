/**
 * NeuroMango — Lip Sync Controller
 * Applies viseme weight data to VRM model blend shapes with smooth interpolation.
 */

// VRM expression names mapped from our viseme IDs
const VISEME_TO_VRM_EXPRESSION = {
    'aa': 'aa',   // Wide open mouth (あ)
    'ih': 'ih',   // Narrow smile (い)
    'ou': 'ou',   // Rounded lips (う)
    'ee': 'ee',   // Mid open (え)
    'oh': 'oh',   // Rounded open (お)
};

export class LipSyncController {
    /**
     * @param {import('@pixiv/three-vrm').VRM} vrm - The loaded VRM model instance
     * @param {object} options - Configuration
     * @param {number} options.smoothing - LERP factor (0-1, lower = smoother)
     */
    constructor(vrm, options = {}) {
        this.vrm = vrm;
        this.smoothing = options.smoothing ?? 0.35;

        // Current viseme weights (what's being displayed)
        this.currentWeights = {
            aa: 0, ih: 0, ou: 0, ee: 0, oh: 0,
        };

        // Target viseme weights (what we're interpolating towards)
        this.targetWeights = {
            aa: 0, ih: 0, ou: 0, ee: 0, oh: 0,
        };

        this.isSpeaking = false;
        this._idleBlinkTimer = 0;
        this._idleBreathTimer = 0;
    }

    /**
     * Set target viseme weights from server data.
     * @param {object} visemes - Map of viseme IDs to weights (0-1)
     */
    setVisemes(visemes) {
        // Reset all targets first
        for (const key of Object.keys(this.targetWeights)) {
            this.targetWeights[key] = 0;
        }
        // Apply new targets
        for (const [id, weight] of Object.entries(visemes)) {
            if (id in this.targetWeights) {
                this.targetWeights[id] = Math.max(0, Math.min(1, weight));
            }
        }
    }

    /** Signal that speech has started. */
    startSpeaking() {
        this.isSpeaking = true;
    }

    /** Signal that speech has ended — smoothly close mouth. */
    stopSpeaking() {
        this.isSpeaking = false;
        for (const key of Object.keys(this.targetWeights)) {
            this.targetWeights[key] = 0;
        }
    }

    /**
     * Update the VRM model's expressions. Call this every frame.
     * @param {number} deltaTime - Time since last frame in seconds
     */
    update(deltaTime) {
        if (!this.vrm || !this.vrm.expressionManager) return;

        const lerpFactor = 1 - Math.pow(1 - this.smoothing, deltaTime * 60);

        // Interpolate current weights towards target
        for (const [visemeId, targetWeight] of Object.entries(this.targetWeights)) {
            const current = this.currentWeights[visemeId];
            this.currentWeights[visemeId] = current + (targetWeight - current) * lerpFactor;

            // Apply to VRM expression
            const expressionName = VISEME_TO_VRM_EXPRESSION[visemeId];
            if (expressionName) {
                this.vrm.expressionManager.setValue(expressionName, this.currentWeights[visemeId]);
            }
        }

        // Idle animations
        this._updateIdleAnimations(deltaTime);
    }

    /** @private */
    _updateIdleAnimations(deltaTime) {
        // Blinking
        this._idleBlinkTimer += deltaTime;
        if (this._idleBlinkTimer > 3 + Math.random() * 4) {
            this._idleBlinkTimer = 0;
            this._triggerBlink();
        }
    }

    /** @private */
    async _triggerBlink() {
        if (!this.vrm?.expressionManager) return;

        const blinkDuration = 0.1;  // seconds
        const steps = 6;

        // Close eyes
        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            this.vrm.expressionManager.setValue('blink', t);
            await this._sleep(blinkDuration / steps * 1000);
        }

        // Open eyes
        for (let i = steps; i >= 0; i--) {
            const t = i / steps;
            this.vrm.expressionManager.setValue('blink', t);
            await this._sleep(blinkDuration / steps * 1000);
        }
    }

    /** @private */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
