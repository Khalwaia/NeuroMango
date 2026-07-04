using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class ChatInputUI : MonoBehaviour
{
    public TMP_InputField inputField;
    public Button sendButton;
    public WebSocketClient webSocketClient;

    void Start()
    {
        if (webSocketClient == null) webSocketClient = GetComponent<WebSocketClient>();
        
        if (sendButton != null) sendButton.onClick.AddListener(OnSendClicked);
        if (inputField != null) inputField.onSubmit.AddListener(OnSubmit);
    }

    void OnSendClicked()
    {
        SendText();
    }

    void OnSubmit(string text)
    {
        SendText();
        if (inputField != null) inputField.ActivateInputField(); // Keep focus
    }



    void SendText()
    {
        if (inputField == null || webSocketClient == null) return;
        
        string text = inputField.text.Trim();
        if (!string.IsNullOrEmpty(text))
        {
            webSocketClient.SendSpeakRequest(text);
            inputField.text = "";
        }
    }
}
