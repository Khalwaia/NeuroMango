/**
 * NeuroMango — Idle Body Animation Controller
 * Procedural animations for VRM model: breathing, body sway, head micro-movements.
 */

export class IdleAnimationController {
    /**
     * @param {import('@pixiv/three-vrm').VRM} vrm
     */
    constructor(vrm) {
        this.vrm = vrm;
        this.elapsed = 0;

        // Cache bone nodes and their base quaternions
        this.bones = {};
        const boneNames = [
            'hips', 'spine', 'chest', 'upperChest',
            'neck', 'head',
            'leftShoulder', 'rightShoulder',
            'leftUpperArm', 'rightUpperArm',
            'leftLowerArm', 'rightLowerArm',
        ];

        for (const name of boneNames) {
            const node = vrm.humanoid?.getNormalizedBoneNode(name);
            if (node) {
                this.bones[name] = {
                    node,
                    baseQuaternion: node.quaternion.clone(),
                };
            }
        }

        console.log('[Idle] Cached bones:', Object.keys(this.bones).join(', '));
    }

    /**
     * Update procedural body animations. Call every frame.
     * @param {number} deltaTime — seconds since last frame
     */
    update(deltaTime) {
        this.elapsed += deltaTime;
        const t = this.elapsed;

        // Accumulate rotation deltas per bone to avoid overwriting
        const deltas = {};
        const add = (name, rx, ry, rz) => {
            if (!deltas[name]) deltas[name] = { rx: 0, ry: 0, rz: 0 };
            deltas[name].rx += rx;
            deltas[name].ry += ry;
            deltas[name].rz += rz;
        };

        // ── Breathing (slow chest expansion, ~0.2 Hz) ──
        const breathPhase = Math.sin(t * 1.2) * 0.5 + 0.5;  // 0→1
        add('spine',     breathPhase * 0.010, 0, 0);
        add('chest',     breathPhase * 0.007, 0, 0);
        add('upperChest', breathPhase * 0.004, 0, 0);
        // Arms lift slightly with breath
        add('leftUpperArm',  0, 0,  breathPhase * 0.006);
        add('rightUpperArm', 0, 0, -breathPhase * 0.006);

        // ── Body sway (very slow weight shift) ──
        const swayZ = Math.sin(t * 0.35) * 0.008;
        const swayX = Math.cos(t * 0.25 + 0.7) * 0.004;
        add('hips',  swayX * 0.5, 0, swayZ * 0.5);
        add('spine', 0,           0, swayZ);

        // ── Head micro-movements (multiple frequencies for organic feel) ──
        const headX = Math.sin(t * 0.45 + 1.0) * 0.018
                    + Math.sin(t * 1.1  + 3.0) * 0.006;
        const headY = Math.sin(t * 0.30 + 2.0) * 0.025
                    + Math.cos(t * 0.80 + 1.5) * 0.008;
        const headZ = Math.cos(t * 0.22 + 0.5) * 0.010;
        add('head', headX, headY, headZ);

        // Neck follows head at ~30%
        add('neck', headX * 0.3, headY * 0.2, headZ * 0.2);

        // ── Shoulder micro-sway ──
        const shoulderPhase = Math.sin(t * 0.5 + 1.2) * 0.005;
        add('leftShoulder',  0, 0,  shoulderPhase);
        add('rightShoulder', 0, 0, -shoulderPhase);

        // ── Arm subtle movement ──
        const armSway = Math.sin(t * 0.28 + 0.3) * 0.012;
        add('leftLowerArm',  armSway * 0.5, 0, 0);
        add('rightLowerArm', armSway * 0.5, 0, 0);

        // Apply all accumulated deltas
        for (const [name, delta] of Object.entries(deltas)) {
            this._applyDelta(name, delta.rx, delta.ry, delta.rz);
        }
    }

    /** @private Apply rotation delta to bone, relative to its rest pose. */
    _applyDelta(name, rx, ry, rz) {
        const boneData = this.bones[name];
        if (!boneData) return;

        const { node, baseQuaternion } = boneData;
        node.quaternion.copy(baseQuaternion);
        node.rotateX(rx);
        node.rotateY(ry);
        node.rotateZ(rz);
    }
}
