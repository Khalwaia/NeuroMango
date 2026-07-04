using UnityEngine;
using System.Collections;
using System.Text;
using System;
using NativeWebSocket;

[Serializable]
public class SpeakMessage {
    public string type;
    public string text;
    public string audio_url; // Legacy
    public float[] visemes;
    public string animation_trigger;
    
    // Streaming fields
    public string audio_base64;
    public int chunk_index;
    public bool is_final;
}

public class WebSocketClient : MonoBehaviour
{
    WebSocket websocket;
    [SerializeField] private string serverUrl = "ws://127.0.0.1:8766/ws";
    public string httpBaseUrl = "http://127.0.0.1:8766";
    
    public AudioStreamPlayer audioPlayer;
    public SubtitleUI subtitleUI;
    private Animator animator;
    public EmotionController emotionController;

    async void Start()
    {
        // Force the correct port in case the Inspector has the old value saved
        serverUrl = "ws://127.0.0.1:8766/ws";
        httpBaseUrl = "http://127.0.0.1:8766";
        
        if (audioPlayer == null) audioPlayer = GetComponent<AudioStreamPlayer>();
        if (subtitleUI == null) subtitleUI = GetComponent<SubtitleUI>();
        
        animator = GetComponentInChildren<Animator>();
        if (animator == null) animator = FindObjectOfType<Animator>();
        
        emotionController = GetComponent<EmotionController>();
        if (emotionController == null) emotionController = gameObject.AddComponent<EmotionController>();

        websocket = new WebSocket(serverUrl);

        websocket.OnOpen += () =>
        {
            Debug.Log("WebSocket Connection open!");
        };

        websocket.OnError += (e) =>
        {
            Debug.LogWarning("WebSocket Error! " + e);
        };

        websocket.OnClose += (e) =>
        {
            Debug.Log("WebSocket Connection closed!");
        };

        websocket.OnMessage += (bytes) =>
        {
            string message = Encoding.UTF8.GetString(bytes);
            try {
                SpeakMessage msg = JsonUtility.FromJson<SpeakMessage>(message);
                
                if (msg.type == "speak_chunk") {
                    if (animator != null && !string.IsNullOrEmpty(msg.animation_trigger)) {
                        Debug.Log("Playing Animation Trigger: " + msg.animation_trigger);
                        animator.SetTrigger(msg.animation_trigger);
                    }
                    
                    if (emotionController != null && !string.IsNullOrEmpty(msg.animation_trigger)) {
                        emotionController.TriggerEmotion(msg.animation_trigger);
                    }
                    
                    if (audioPlayer != null && !string.IsNullOrEmpty(msg.audio_base64)) {
                        Debug.Log("Queueing audio chunk: " + msg.chunk_index);
                        audioPlayer.QueueBase64Audio(msg.audio_base64, msg.visemes, msg.text);
                    }
                } else if (msg.type == "speak_cancel") {
                    if (audioPlayer != null) audioPlayer.StopPlayback();
                    if (emotionController != null) emotionController.TriggerEmotion("Idle");
                } else if (msg.type == "emotion") {
                    if (emotionController != null && !string.IsNullOrEmpty(msg.animation_trigger)) {
                        emotionController.TriggerEmotion(msg.animation_trigger);
                    }
                } else if (msg.type == "speak_done") {
                    Debug.Log("Server finished generating all chunks.");
                    if (emotionController != null) emotionController.TriggerEmotion("Idle");
                }
            } catch (Exception e) {
                Debug.LogWarning("Failed to parse JSON message: " + e.Message);
            }
        };

        InvokeRepeating("SendPing", 1.0f, 5.0f);
        await websocket.Connect();
    }

    void Update()
    {
        #if !UNITY_WEBGL || UNITY_EDITOR
        if (websocket != null)
        {
            websocket.DispatchMessageQueue();
        }
        #endif
    }
    
    void SendPing() {
        if (websocket.State == WebSocketState.Open) {
            websocket.SendText("{\"type\": \"ping\"}");
        }
    }

    public async void SendSpeakRequest(string text)
    {
        if (websocket.State == WebSocketState.Open)
        {
            SpeakMessage msg = new SpeakMessage { type = "speak", text = text };
            string json = JsonUtility.ToJson(msg);
            await websocket.SendText(json);
        }
    }

    private async void OnApplicationQuit()
    {
        if (websocket != null) {
            await websocket.Close();
        }
    }
}
