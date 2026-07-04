using UnityEngine;
using VRM;
using System.Collections;
using System.Collections.Generic;

public class EmotionController : MonoBehaviour
{
    private VRMBlendShapeProxy vrmProxy;
    
    // Emotion mapping dictionary (case-insensitive)
    private Dictionary<string, BlendShapeKey> emotionMap = new Dictionary<string, BlendShapeKey>(System.StringComparer.OrdinalIgnoreCase)
    {
        { "Smile", BlendShapeKey.CreateFromPreset(BlendShapePreset.Joy) },
        { "Joy", BlendShapeKey.CreateFromPreset(BlendShapePreset.Joy) },
        { "Angry", BlendShapeKey.CreateFromPreset(BlendShapePreset.Angry) },
        { "Sad", BlendShapeKey.CreateFromPreset(BlendShapePreset.Sorrow) },
        { "Sorrow", BlendShapeKey.CreateFromPreset(BlendShapePreset.Sorrow) },
        { "Fun", BlendShapeKey.CreateFromPreset(BlendShapePreset.Fun) },
        { "Surprise", BlendShapeKey.CreateUnknown("Surprised") },
        { "Surprised", BlendShapeKey.CreateUnknown("Surprised") },
        { "Idle", BlendShapeKey.CreateFromPreset(BlendShapePreset.Neutral) },
        { "Think", BlendShapeKey.CreateFromPreset(BlendShapePreset.Neutral) },
        { "Wave", BlendShapeKey.CreateFromPreset(BlendShapePreset.Neutral) },
        
        // Новые кастомные эмоции со скриншотов
        { "Annoyed", BlendShapeKey.CreateUnknown("Annoyed") },
        { "Shocked", BlendShapeKey.CreateUnknown("Shocked") },
        { "Frustrated", BlendShapeKey.CreateUnknown("Frustrated") },
        { "Dizzy", BlendShapeKey.CreateUnknown("Dizzy") }
    };
    
    private BlendShapeKey currentEmotion;
    private BlendShapeKey neutralEmotion;
    private Coroutine transitionCoroutine;

    private VRM.Blinker vrmBlinker;
    
    // Emotions that shouldn't have blinking active to prevent glitches
    private HashSet<string> noBlinkEmotions = new HashSet<string>(System.StringComparer.OrdinalIgnoreCase)
    {
        "Smile", "Joy", "Angry", "Sad", "Sorrow", "Fun", 
        "Annoyed", "Frustrated", "Dizzy"
    };

    void Start()
    {
        vrmProxy = GetComponentInChildren<VRMBlendShapeProxy>();
        if (vrmProxy == null) vrmProxy = FindObjectOfType<VRMBlendShapeProxy>();
        
        vrmBlinker = GetComponentInChildren<VRM.Blinker>();
        if (vrmBlinker == null) vrmBlinker = FindObjectOfType<VRM.Blinker>();
        
        neutralEmotion = BlendShapeKey.CreateFromPreset(BlendShapePreset.Neutral);
        currentEmotion = neutralEmotion;
    }

    public void TriggerEmotion(string emotionTag)
    {
        if (vrmProxy == null) return;
        
        // Handle blinker state
        if (vrmBlinker != null)
        {
            vrmBlinker.enabled = !noBlinkEmotions.Contains(emotionTag);
        }
        
        if (emotionMap.ContainsKey(emotionTag))
        {
            BlendShapeKey targetEmotion = emotionMap[emotionTag];
            
            if (!targetEmotion.Equals(currentEmotion))
            {
                if (transitionCoroutine != null) StopCoroutine(transitionCoroutine);
                transitionCoroutine = StartCoroutine(TransitionEmotion(currentEmotion, targetEmotion, 0.5f));
                currentEmotion = targetEmotion;
            }
        }
        else
        {
            // Revert to neutral
            if (!currentEmotion.Equals(neutralEmotion))
            {
                if (transitionCoroutine != null) StopCoroutine(transitionCoroutine);
                transitionCoroutine = StartCoroutine(TransitionEmotion(currentEmotion, neutralEmotion, 0.5f));
                currentEmotion = neutralEmotion;
            }
            if (vrmBlinker != null) vrmBlinker.enabled = true; // Neutral usually blinks
        }
    }

    private IEnumerator TransitionEmotion(BlendShapeKey from, BlendShapeKey to, float duration)
    {
        float elapsed = 0f;
        
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float t = elapsed / duration;
            // Smoothstep
            float smooth_t = t * t * (3f - 2f * t);
            
            if (!from.Equals(neutralEmotion))
                vrmProxy.ImmediatelySetValue(from, 1f - smooth_t);
                
            if (!to.Equals(neutralEmotion))
                vrmProxy.ImmediatelySetValue(to, smooth_t);
                
            yield return null;
        }
        
        if (!from.Equals(neutralEmotion))
            vrmProxy.ImmediatelySetValue(from, 0f);
            
        if (!to.Equals(neutralEmotion))
            vrmProxy.ImmediatelySetValue(to, 1f);
    }
}
