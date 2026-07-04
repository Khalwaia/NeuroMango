using UnityEngine;
using VRM;

public class VRMAlive : MonoBehaviour
{
    private Animator animator;
    private Transform neck, head;

    private Quaternion iNeck, iHead;
    private VRMBlendShapeProxy vrmProxy;

    [Header("Looking Around (Head & Eyes)")]
    public float lookIntervalMin = 2f;
    public float lookIntervalMax = 6f;
    public float maxHeadAngle = 5f; 
    public float maxEyeDistance = 1.5f; // Насколько далеко бегают глаза (в метрах)
    private float lookTimer;
    private Quaternion targetHeadLook = Quaternion.identity;
    private Quaternion currentHeadLook = Quaternion.identity;
    
    // Безопасное управление глазами через стандартный плагин VRM
    private VRMLookAtHead vrmLookAt;
    private Transform eyeTarget;
    private Vector3 targetEyePos;

    [Header("Blinking")]
    public float blinkIntervalMin = 2.5f;
    public float blinkIntervalMax = 6f;
    private float blinkTimer;
    private bool isBlinking;
    private float blinkProgress;

    [Header("Breathing (Sway)")]
    public float breathSpeed = 1.5f;
    public float breathAngle = 2f;
    private Transform spine;
    private Quaternion iSpine;

    [Header("Arms (T-Pose Fix)")]
    public Vector3 leftArmDrop = new Vector3(0, 0, -70f);
    public Vector3 rightArmDrop = new Vector3(0, 0, 70f);
    private Transform leftArm, rightArm;
    private Quaternion iLeftArm, iRightArm;

    void Start()
    {
        animator = GetComponentInChildren<Animator>();
        if (animator == null) animator = FindObjectOfType<Animator>();

        if (animator != null)
        {
            neck = animator.GetBoneTransform(HumanBodyBones.Neck);
            head = animator.GetBoneTransform(HumanBodyBones.Head);
            spine = animator.GetBoneTransform(HumanBodyBones.Spine);
            leftArm = animator.GetBoneTransform(HumanBodyBones.LeftUpperArm);
            rightArm = animator.GetBoneTransform(HumanBodyBones.RightUpperArm);

            if (neck) iNeck = neck.localRotation;
            if (head) iHead = head.localRotation;
            if (spine) iSpine = spine.localRotation;
            if (leftArm) iLeftArm = leftArm.localRotation;
            if (rightArm) iRightArm = rightArm.localRotation;
        }

        vrmProxy = GetComponentInChildren<VRMBlendShapeProxy>();
        if (vrmProxy == null) vrmProxy = FindObjectOfType<VRMBlendShapeProxy>();
        
        vrmLookAt = GetComponentInChildren<VRMLookAtHead>();
        if (vrmLookAt == null) vrmLookAt = FindObjectOfType<VRMLookAtHead>();
        
        if (vrmLookAt != null)
        {
            eyeTarget = new GameObject("VRM_EyeTarget").transform;
            // Ставим цель в 3 метрах перед лицом
            if (head != null)
                eyeTarget.position = head.position + head.forward * 3f;
            else
                eyeTarget.position = transform.position + transform.forward * 3f + Vector3.up * 1.5f;
                
            vrmLookAt.Target = eyeTarget;
            targetEyePos = eyeTarget.localPosition;
        }

        ResetLookTimer();
        ResetBlinkTimer();
    }

    void ResetLookTimer() { lookTimer = Random.Range(lookIntervalMin, lookIntervalMax); }
    void ResetBlinkTimer() { blinkTimer = Random.Range(blinkIntervalMin, blinkIntervalMax); }

    void LateUpdate()
    {
        UpdateBlinking();
        UpdateLooking();

        // Небольшой поворот шеи и головы
        if (neck)
            neck.localRotation = iNeck * currentHeadLook;

        if (head)
            head.localRotation = iHead * currentHeadLook;
            
        // Дыхание (покачивание грудной клетки/спины)
        if (spine)
        {
            float breath = Mathf.Sin(Time.time * breathSpeed) * breathAngle;
            spine.localRotation = iSpine * Quaternion.Euler(breath, 0, 0);
        }

        // Lower arms to avoid T-Pose (Guaranteed method using World Space)
        if (leftArm)
        {
            leftArm.localRotation = iLeftArm; 
            Quaternion dropRot = Quaternion.AngleAxis(70f, Vector3.forward) * Quaternion.AngleAxis(15f, Vector3.right);
            leftArm.rotation = dropRot * leftArm.rotation;
        }
        if (rightArm)
        {
            rightArm.localRotation = iRightArm; 
            Quaternion dropRot = Quaternion.AngleAxis(-70f, Vector3.forward) * Quaternion.AngleAxis(15f, Vector3.right);
            rightArm.rotation = dropRot * rightArm.rotation;
        }
    }

    void UpdateLooking()
    {
        lookTimer -= Time.deltaTime;
        if (lookTimer <= 0)
        {
            float headPitch = Random.Range(-maxHeadAngle, maxHeadAngle);
            float headYaw = Random.Range(-maxHeadAngle, maxHeadAngle);
            targetHeadLook = Quaternion.Euler(headPitch, headYaw, 0);
            
            if (eyeTarget != null)
            {
                // Сдвигаем точку интереса (цель для глаз)
                float offsetX = Random.Range(-maxEyeDistance, maxEyeDistance);
                float offsetY = Random.Range(-maxEyeDistance, maxEyeDistance);
                
                Transform origin = head != null ? head : transform;
                targetEyePos = origin.position + origin.forward * 3f + origin.right * offsetX + origin.up * offsetY;
            }
            
            ResetLookTimer();
        }
        
        currentHeadLook = Quaternion.Slerp(currentHeadLook, targetHeadLook, Time.deltaTime * 2f);
        
        if (eyeTarget != null)
        {
            eyeTarget.position = Vector3.Lerp(eyeTarget.position, targetEyePos, Time.deltaTime * 3f);
        }
    }

    void UpdateBlinking()
    {
        if (vrmProxy == null) return;

        // Отключаем моргание во время улыбки, чтобы глаза не "вдавливались"
        if (vrmProxy.GetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.Joy)) > 0.1f ||
            vrmProxy.GetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.Fun)) > 0.1f)
        {
            if (isBlinking) {
                isBlinking = false;
                vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink), 0f);
            }
            return;
        }

        if (!isBlinking)
        {
            blinkTimer -= Time.deltaTime;
            if (blinkTimer <= 0)
            {
                isBlinking = true;
                blinkProgress = 0f;
            }
        }
        else
        {
            blinkProgress += Time.deltaTime * 8f; 
            float blinkValue = Mathf.PingPong(blinkProgress, 1f);
            vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink), blinkValue);

            if (blinkProgress >= 2f)
            {
                isBlinking = false;
                vrmProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink), 0f);
                ResetBlinkTimer();
            }
        }
    }
}
