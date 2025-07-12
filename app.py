from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from forms import RegisterForm, LoginForm
from forms import JournalForm
from flask_wtf import CSRFProtect
import openai
from flask_wtf.csrf import CSRFError
import requests
import traceback
from flask import request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from langdetect import detect
from flask_migrate import Migrate
import uuid
from TTS.api import TTS as CoquiTTS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()




app=Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key='shyama_here'

coqui_tts = CoquiTTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False, gpu=False)

clean_speakers = [s.strip() for s in coqui_tts.speakers]
print("✅ Cleaned available speakers:", clean_speakers)



app.config['WTF_CSRF_ENABLED'] = True

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db=SQLAlchemy(app)
bcrypt=Bcrypt(app)
migrate = Migrate(app, db)

class User(db.Model):
  id=db.Column(db.Integer, primary_key=True)
  username=db.Column(db.String(100), unique=True, nullable=False)
  password=db.Column(db.String(100), nullable=False)


with app.app_context():
  db.create_all()


class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
  db.create_all()


class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(10))  # "user", "assistant", "system"
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



with app.app_context():
    db.create_all()

   
   
  


@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()

    # ✅ This fetches the latest journal entry
    latest_entry = JournalEntry.query.filter_by(user_id=user.id)\
                                     .order_by(JournalEntry.timestamp.desc())\
                                     .first()

    # ✅ Generate mood_data and frequency_data
    entries = JournalEntry.query.filter_by(user_id=user.id).order_by(JournalEntry.timestamp).all()

    mood_data = {
        "labels": [e.timestamp.strftime("%Y-%m-%d") for e in entries],
        "values": [SentimentIntensityAnalyzer().polarity_scores(e.content)['compound'] for e in entries]
    }

    frequency_data = {
        "labels": list(dict((e.timestamp.strftime("%Y-%m-%d"), 0) for e in entries).keys()),
        "values": [1 for _ in entries]
    }

    return render_template("home.html",
                           username=user.username,
                           mood_data=mood_data,
                           frequency_data=frequency_data,
                           latest_entry=latest_entry)







@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash( "Username already exists!")
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)



@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)




@app.route('/logout')
def logout():
  session.pop('username', None)
  return redirect(url_for('login'))


@app.route("/journal", methods=['GET', 'POST'])
def journal():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    form = JournalForm()

    if form.validate_on_submit():
        entry = JournalEntry(
            user_id=user.id,
            title=form.title.data,  # use title from form
            content=form.content.data
        )
        db.session.add(entry)
        db.session.commit()
        flash("Journal entry saved!")
        return redirect(url_for('journal'))

    # Fetch entries for display
    entries = JournalEntry.query.filter_by(user_id=user.id).order_by(JournalEntry.timestamp.desc()).all()

    # Check if the request is for events (calendar AJAX request)
    if request.args.get('format') == 'json':
        events = []
        for entry in entries:
            events.append({
                "id": entry.id,
                "title": entry.title,
                "start": entry.timestamp.strftime("%Y-%m-%d")
            })
        return jsonify(events)

    # Otherwise, render the journal page
    return render_template("journal.html", username=user.username, form=form, entries=entries)

@csrf.exempt  
@app.route("/delete_entry/<int:entry_id>", methods=['POST'])
def delete_entry(entry_id):
    if'username' not in session:
      return redirect(url_for('login'))
    entry=JournalEntry.query.get_or_404(entry_id)
    user=User.query.filter_by(username=session['username']).first()
    if entry.user_id!=user.id:
       flash("unauthorized action")
       return redirect(url_for('journal'))
    db.session.delete(entry)
    db.session.commit()
    flash("entry deleted")
    return redirect(url_for('journal'))


@app.route("/edit_entry/<int:entry_id>", methods=['GET', 'POST'])
def edit_entry(entry_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    entry = JournalEntry.query.get_or_404(entry_id)
    user = User.query.filter_by(username=session['username']).first()

    if entry.user_id != user.id:
        flash("Unauthorized action.")
        return redirect(url_for('journal'))

    form = JournalForm()

    if form.validate_on_submit():
        entry.title = form.title.data
        entry.content = form.content.data
        db.session.commit()
        flash("Entry updated.")
        return redirect(url_for('journal'))

    # Pre-fill the form with existing data
    form.title.data = entry.title
    form.content.data = entry.content

    return render_template("edit_entry.html", form=form, entry=entry)


   
   

@app.route("/assistant")
def assistant():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("assistant.html", username=session['username'])

@csrf.exempt
@app.route("/ask", methods=["POST"])
def ask():
    if 'username' not in session:
        return jsonify({"answer": "⚠️ Not logged in"}), 403

    data = request.get_json()
    question = data.get("question")
    selected_lang = data.get("lang")

    user = User.query.filter_by(username=session['username']).first()

    # Sentiment & language detection
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(question)['compound']
    emotion = (
        "positive" if sentiment_score >= 0.5 else
        "negative" if sentiment_score <= -0.5 else
        "neutral"
    )
    try:
        lang = selected_lang  # Always use the language selected in the dropdown
        

    except:
        lang = 'en'

    # Tone for system prompt
    tone_instruction = {
        "positive": "Respond with energy and optimism.",
        "neutral": "Respond with warmth and support.",
        "negative": "Respond gently, with empathy and encouragement."
    }.get(emotion, "Respond with support.")

    if lang != "en":
        tone_instruction += f" The user is speaking in {lang}. Respond in {lang}."


  # Always insert system prompt freshly
    ChatHistory.query.filter_by(user_id=user.id, role='system').delete()
    system_prompt = ChatHistory(
        user_id=user.id,
        role="system",
        content=(
            "You are MindMate, a calm and concise AI assistant. "
            "Reply in 1–2 very short sentences (under 40 words). "
            "Never include roleplay, tone narration, or asterisks like *responds gently*. "
            "Do not explain unless asked. "
           f"Respond in {lang}. Do not say the language name or code in your response."

            "Avoid long replies. Never give medical advice."
        )
    )
    db.session.add(system_prompt)
    db.session.commit()


    # Save user's message
    db.session.add(ChatHistory(user_id=user.id, role="user", content=question))
    db.session.commit()

    history_entries = ChatHistory.query.filter_by(user_id=user.id).order_by(ChatHistory.timestamp).all()

    # Keep only last 8 (4 pairs) + system
    if len(history_entries) > 9:
        system_prompt = history_entries[0]
        last_8 = history_entries[-8:]
        history_entries = [system_prompt] + last_8


    # Format for Claude
    def format_for_claude(history):
        return [
            {
                "role": h.role,
                "content": [{"type": "text", "text": h.content}]
            } for h in history
        ]

    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": format_for_claude(history_entries)
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "HTTP-Referer": "http://localhost:5000",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]

            # Save assistant reply
            db.session.add(ChatHistory(user_id=user.id, role="assistant", content=answer))
            db.session.commit()

            return jsonify({"answer": answer})
        else:
            error_msg = data.get("error", "⚠️ No 'choices' in response")
            return jsonify({"answer": f"⚠️ OpenRouter error: {error_msg}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"answer": f"⚠️ Could not connect to MindMate. {str(e)}"}), 500


@app.route("/reset_history", methods=["POST"])
def reset_history():
    if 'username' not in session:
        return '', 204
    user = User.query.filter_by(username=session['username']).first()
    ChatHistory.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return '', 204

@app.route("/view_chat")
def view_chat():
    if 'username' not in session:
        return "❌ You must be logged in", 403

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return "❌ User not found", 404

    messages = ChatHistory.query.filter_by(user_id=user.id).order_by(ChatHistory.timestamp).all()

    output = "<h2>🧠 Chat History</h2>"
    for msg in messages:
        output += f"<p><strong>{msg.timestamp} [{msg.role}]</strong>: {msg.content}</p>"

    return output




@csrf.exempt
@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", "en")  # e.g. 'en-US'
    speaker = data.get("speaker", "en_0")  # Replace with a valid speaker

    # Map browser lang to Coqui-supported lang
    lang_map = {
        "en-US": "en",
        "fr-FR": "fr-fr",
        "pt-PT": "pt-br",
        "hi-IN": "en",
        "ta-IN": "en",
        "bn-IN": "en",
        "es-ES": "en",
        "zh-CN": "en",
        "ar-SA": "en",
        "de-DE": "en"
    }
    coqui_lang = lang_map.get(lang, "en")

    try:
        print("🗣️ Text to Speak:", text)
        print("🧑 Speaker:", speaker)
        print("🌍 Language:", coqui_lang)

        filename = f"tts_{uuid.uuid4().hex}.wav"
        output_path = os.path.join("static", filename)

        coqui_tts.tts_to_file(
            text=text,
            speaker=speaker,
            language=coqui_lang,
            file_path=output_path
        )

        if not os.path.exists(output_path):
            print("❌ File not created:", output_path)
            return jsonify({"error": "TTS failed: audio file not generated"}), 500

        print(f"✅ Audio file saved to: {output_path}")
        return jsonify({"audio_url": f"/static/{filename}"})

    except Exception as e:
        print("❌ TTS Generation Error:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500





# @app.route("/debug_chat_schema")
# def debug_chat_schema():
#     from sqlalchemy import inspect
#     inspector = inspect(db.engine)
#     return {"tables": inspector.get_table_names()}
 


@app.route("/audio")
def audio():
    if 'username' not in session:
        return redirect(url_for('login'))

    moods = [
        {
            "name": "Calm & Peaceful",
            "tracks": [
                {"name": "Ocean Waves", "src": "/static/audio/calm1.mp3"},
                {"name": "Gentle Rain", "src": "/static/audio/calm2.mp3"},
                {"name": "Soft Wind", "src": "/static/audio/calm3.mp3"},
            ],
            "bg": "/static/calm.avif"
        },
        {
            "name": "Focus & Clarity",
           
            "tracks": [
                {"name": "Deep Focus", "src": "/static/audio/focus1.mp3"},
                {"name": "Alpha Waves", "src": "/static/audio/focus2.mp3"},
                {"name": "Flow State", "src": "/static/audio/focus3.mp3"},
            ],
            "bg": "/static/focus.jpg"
        },
        {
            "name": "Energy & Motivation",
            
            "tracks": [
                {"name": "Power Boost", "src": "/static/audio/energy1.mp3"},
                {"name": "Morning Hype", "src": "/static/audio/energy2.mp3"},
                {"name": "Victory Vibes", "src": "/static/audio/energy3.mp3"},
            ],
            "bg": "/static/energy.jpg"
        },
        {
            "name": "Meditation",
           
            "tracks": [
                {"name": "Stillness", "src": "/static/audio/meditate1.mp3"},
                {"name": "Inner Peace", "src": "/static/audio/meditate2.mp3"},
                {"name": "Mindful Moments", "src": "/static/audio/meditate3.mp3"},
            ],
            "bg": "/static/mediation.jpg"
        },
        {
            "name": "Nature Sounds",
           
            "tracks": [
                {"name": "Forest Walk", "src": "/static/audio/nature1.mp3"},
                {"name": "Birdsong", "src": "/static/audio/nature2.mp3"},
                {"name": "River Stream", "src": "/static/audio/nature3.mp3"},
            ],
            "bg": "/static/nature.webp"
        },
        {
            "name": "Sleep & Rest",
            
            "tracks": [
                {"name": "Night Wind", "src": "/static/audio/sleep1.mp3"},
                {"name": "Lullaby Drift", "src": "/static/audio/sleep2.mp3"},
                {"name": "Dreamscape", "src": "/static/audio/sleep3.mp3"},
            ],
            "bg": "/static/sleep.webp"
        },
    ]

    return render_template('audio.html', username=session['username'], moods=moods)


if __name__ == '__main__':
    app.run(debug=True)