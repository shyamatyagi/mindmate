import requests

data = {
    "text": "नमस्ते, आप कैसे हैं?",
    "voice": "espeak:hi"
}

res = requests.post("http://localhost:5500/api/tts", json=data)

print(res.status_code)
if res.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(res.content)
    print("✅ Audio saved as output.wav")
else:
    print(f"❌ Error {res.status_code}: {res.text}")
