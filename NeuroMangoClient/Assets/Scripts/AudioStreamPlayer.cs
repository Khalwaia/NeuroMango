using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System;
using System.IO;

public class AudioChunk {
    public AudioClip clip;
    public float[] visemes;
    public string text;
}

[RequireComponent(typeof(AudioSource))]
public class AudioStreamPlayer : MonoBehaviour
{
    private AudioSource audioSource;
    public SubtitleUI subtitleUI;
    
    private float[] currentVisemes;
    private const float VISEME_CHUNK_MS = 50f;
    
    private Queue<AudioChunk> chunkQueue = new Queue<AudioChunk>();
    private bool isPlayingChunk = false;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
    }

    void Update()
    {
        if (!isPlayingChunk && chunkQueue.Count > 0)
        {
            StartCoroutine(PlayNextChunk());
        }
    }

    private IEnumerator PlayNextChunk()
    {
        isPlayingChunk = true;
        AudioChunk chunk = chunkQueue.Dequeue();
        
        if (subtitleUI != null && !string.IsNullOrEmpty(chunk.text)) {
            subtitleUI.ShowSubtitle(chunk.text);
        }
        
        currentVisemes = chunk.visemes;
        audioSource.clip = chunk.clip;
        audioSource.Play();
        
        // XTTS typically adds a small amount of trailing silence (padding).
        // To eliminate gaps between sentences, we stop waiting ~200ms early.
        // If there's another chunk in the queue, it will immediately cut off the silence and play.
        float waitTime = Mathf.Max(0.1f, chunk.clip.length - 0.2f);
        yield return new WaitForSeconds(waitTime);
        
        isPlayingChunk = false;
        
        if (chunkQueue.Count == 0 && subtitleUI != null) {
            yield return new WaitForSeconds(0.2f); // Finish the remaining padding time visually
            subtitleUI.HideSubtitle();
        }
    }

    public float GetCurrentViseme()
    {
        if (currentVisemes == null || currentVisemes.Length == 0 || !audioSource.isPlaying) return 0f;
        
        int index = Mathf.FloorToInt((audioSource.time * 1000f) / VISEME_CHUNK_MS);
        if (index >= 0 && index < currentVisemes.Length) {
            return currentVisemes[index];
        }
        return 0f;
    }

    public void QueueBase64Audio(string base64Data, float[] visemes, string text)
    {
        StartCoroutine(DecodeAndQueueBase64(base64Data, visemes, text));
    }
    
    private IEnumerator DecodeAndQueueBase64(string base64Data, float[] visemes, string text)
    {
        byte[] audioBytes = Convert.FromBase64String(base64Data);
        string tempPath = Application.temporaryCachePath + "/temp_chunk_" + Guid.NewGuid().ToString() + ".wav";
        File.WriteAllBytes(tempPath, audioBytes);
        
        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip("file://" + tempPath, AudioType.WAV))
        {
            yield return www.SendWebRequest();
            if (www.result == UnityWebRequest.Result.Success)
            {
                AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                if (clip != null) {
                    chunkQueue.Enqueue(new AudioChunk { clip = clip, visemes = visemes, text = text });
                }
            }
        }
        
        try { File.Delete(tempPath); } catch {}
    }

    public void StopPlayback() {
        StopAllCoroutines();
        audioSource.Stop();
        chunkQueue.Clear();
        isPlayingChunk = false;
        if (subtitleUI != null) subtitleUI.HideSubtitle();
    }
}
