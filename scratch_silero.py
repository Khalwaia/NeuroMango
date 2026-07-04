import os
import torch
import torchaudio
import time
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def test_silero():
    device = torch.device('cpu') # Test on CPU first for simplicity, maybe CUDA if available
    if torch.cuda.is_available():
        device = torch.device('cuda')
        
    torch.set_num_threads(4)
    local_file = 'v4_ru.pt'

    if not os.path.isfile(local_file):
        print("Downloading Silero V4 model...")
        torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v4_ru.pt',
                                       local_file)  

    print("Loading model...")
    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
    model.to(device)

    sample_rate = 48000
    speaker='baya' # or xenia, kseniya, aidar
    
    # Text to test SSML features like prosody
    text = "<speak><prosody pitch=\"x-high\" rate=\"fast\">Ааааааа! Это же крик демона!</prosody></speak>"

    print(f"Generating audio for text: {text}")
    start = time.time()
    
    try:
        audio = model.apply_tts(text=text,
                                speaker=speaker,
                                sample_rate=sample_rate)
        elapsed = time.time() - start
        print(f"Generation took {elapsed:.2f}s")
        
        # Save to file
        torchaudio.save('test_scream.wav', audio.unsqueeze(0), sample_rate)
        print("Saved to test_scream.wav")
    except Exception as e:
        print(f"Failed to generate: {e}")

if __name__ == "__main__":
    test_silero()
