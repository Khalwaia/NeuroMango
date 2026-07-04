using UnityEngine;
using TMPro;

public class SubtitleUI : MonoBehaviour
{
    public TextMeshProUGUI subtitleText;
    public CanvasGroup canvasGroup;

    void Start()
    {
        if (canvasGroup != null) canvasGroup.alpha = 0;
    }

    public void ShowSubtitle(string text)
    {
        if (subtitleText == null || canvasGroup == null) return;
        subtitleText.text = text;
        StopAllCoroutines();
        StartCoroutine(FadeTo(1.0f, 0.25f));
    }

    public void HideSubtitle()
    {
        if (canvasGroup == null) return;
        StopAllCoroutines();
        StartCoroutine(FadeTo(0.0f, 0.5f));
    }

    private System.Collections.IEnumerator FadeTo(float targetAlpha, float duration)
    {
        float startAlpha = canvasGroup.alpha;
        float time = 0;
        while (time < duration)
        {
            time += Time.deltaTime;
            canvasGroup.alpha = Mathf.Lerp(startAlpha, targetAlpha, time / duration);
            yield return null;
        }
        canvasGroup.alpha = targetAlpha;
    }
}
