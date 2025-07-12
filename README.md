# 🧠 MindMate – Your Mental Wellness Companion

MindMate is a personalized AI-powered mental wellness assistant built using Flask.  
It allows users to journal their thoughts, chat with an AI in multiple languages, listen to relaxing audio sessions, and track emotional trends over time — all in a secure and engaging interface.

---

## 🌟 Features

### 🗣️ Multilingual Chat with AI
- Talk to an intelligent assistant in **English, Hindi, Tamil, French, Spanish, German, Bengali, Arabic, Chinese**, and more
- Supports **voice input** and **voice responses** using speech recognition and Coqui TTS
- Automatically adjusts tone based on detected sentiment (positive/neutral/negative)

### 📓 Private Journal
- Secure, daily journaling system
- Save and edit your thoughts
- AI performs sentiment analysis on each entry to detect your mood

### 📈 Mood Trends & Streaks
- Track your **emotional trend** over time with a graph
- See your **journaling streaks** to stay consistent

### 🎵 Audio Therapy Library
- Browse by mood: **Calm**, **Focus**, **Energy**, **Sleep**, **Nature**, **Meditation**
- Listen to built-in relaxing soundtracks directly in the app

### 🔐 Secure User System
- Register and log in to your own private dashboard
- Data is stored securely using SQLite and Flask sessions

---

## 📷 Screenshots
### Home Page
<img width="975" height="469" alt="image" src="https://github.com/user-attachments/assets/43dc1267-9674-4b10-8706-76859ba26002" />

<img width="975" height="456" alt="image" src="https://github.com/user-attachments/assets/cfbdf33b-2a00-4fb5-a1b6-f2d2e77c5b90" />

### 🧠 AI Assistant Chat
<img width="975" height="498" alt="image" src="https://github.com/user-attachments/assets/09cb7b8a-c1d7-4b07-83c0-67ec669f4d69" />

<img width="975" height="490" alt="image" src="https://github.com/user-attachments/assets/66dbe53d-fff7-41cf-b091-867d12c5e108" />




### 📓 Journal & Sentiment Graph
<img width="975" height="681" alt="image" src="https://github.com/user-attachments/assets/5f577508-2fd7-4c28-98b2-50b559792b14" />


### 🎧 Audio Player
<img width="975" height="579" alt="image" src="https://github.com/user-attachments/assets/1205ebbb-5f84-4551-8908-a6ab48083d0f" />

## ⚙️ Getting Started

### 1. Clone this Repository
```bash
git clone https://github.com/your-username/mindmate-app.git
cd mindmate-app
```
### 2. Create a Virtual Environment (optional but recommended)
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```
### 3. Install Requirements
```bash
pip install -r requirements.txt
```
### 4. Set Up Your .env File
Create a file named `.env` in your project root and add:
```.env
OPENROUTER_API_KEY=your-api-key-here
```
### 5. Run the App
```bash
python app.py
```

