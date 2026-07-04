using UnityEngine;
using CrazyMinnow.SALSA;
using VRM;
using System.Collections.Generic;

public class SalsaVRMSync : MonoBehaviour
{
    public VRMBlendShapeProxy vrmProxy;
    private AudioStreamPlayer audioPlayer;
    private float smoothedViseme = 0f;

    void Start()
    {
        FindVRM();
        audioPlayer = FindObjectOfType<AudioStreamPlayer>();
    }

    void FindVRM()
    {
        if (vrmProxy != null) return;
        
        vrmProxy = GetComponentInParent<VRMBlendShapeProxy>();
        if (vrmProxy == null) vrmProxy = GetComponentInChildren<VRMBlendShapeProxy>();
        if (vrmProxy == null) vrmProxy = FindObjectOfType<VRMBlendShapeProxy>();
        
        if (vrmProxy == null) {
            Debug.LogWarning("SalsaVRMSync: Could not find VRMBlendShapeProxy in the scene yet.");
        }
    }

    void LateUpdate()
    {
        if (audioPlayer == null) audioPlayer = FindObjectOfType<AudioStreamPlayer>();
        if (audioPlayer == null) return;
        
        if (vrmProxy == null) FindVRM();
        if (vrmProxy == null) return;
        
        // Get the target viseme amplitude from the server
        float targetViseme = audioPlayer.GetCurrentViseme();
        
        // Smooth the transition so it looks natural like SALSA
        smoothedViseme = Mathf.Lerp(smoothedViseme, targetViseme, Time.deltaTime * 15f);

        // Map the single amplitude value to VRM Blendshapes (0.0 to 1.0)
        // E (Small), I (Medium), A (Large), O (Round)
        
        float saySmall = Mathf.Clamp(smoothedViseme * 2.0f, 0f, 1f); // Triggers early
        float sayMedium = Mathf.Clamp((smoothedViseme - 0.3f) * 2.0f, 0f, 1f); // Triggers in middle
        float sayLarge = Mathf.Clamp((smoothedViseme - 0.6f) * 2.5f, 0f, 1f); // Triggers only on loud

        vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.E), saySmall * 0.6f);
        vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.I), sayMedium * 0.7f);
        vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.A), sayLarge * 0.5f); // Reduced from 1.0
        vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.O), sayLarge * 0.3f); // Reduced from 0.5
    }
}
