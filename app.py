from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from llm_handler import generate_response
from pymongo import MongoClient
import uuid
import os
import pyttsx3
import whisper
from pydub import AudioSegment
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session
CORS(app)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client.medmate
chat_collection = db.chat_history
user_collection = db.users  # New collection for login/register

# Voice directories
VOICE_DIR = "static/voice"
os.makedirs(VOICE_DIR, exist_ok=True)

# Voice output (TTS)
engine = pyttsx3.init()

# Voice input (STT)
whisper_model = whisper.load_model("base")

# ---------- ROUTES ----------

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = user_collection.find_one({"username": username})

        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))
        return "Invalid credentials. Try again."

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if user_collection.find_one({"username": username}):
            return "Username already exists."

        user_collection.insert_one({
            "username": username,
            "password": password
        })

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/get', methods=['POST'])
def get_bot_response():
    if 'username' not in session:
        return jsonify({'response': 'Unauthorized'}), 401

    try:
        user_input = request.json['message']
        username = session['username']

        # Generate AI response
        response = generate_response(user_input)

        # Save to DB
        chat_id = str(uuid.uuid4())
        chat_collection.insert_one({
            "_id": chat_id,
            "username": username,
            "user_message": user_input,
            "bot_response": response
        })

        # Generate voice output
        voice_path = os.path.join(VOICE_DIR, f"{uuid.uuid4()}.mp3")
        engine.save_to_file(response, voice_path)
        engine.runAndWait()

        return jsonify({
            'response': response,
            'voice_url': '/' + voice_path.replace("\\", "/")
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': 'Something went wrong. Please try again.'})

@app.route("/voice", methods=["POST"])
def voice_to_text():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    audio_file = request.files["audio"]
    filename = f"temp_{uuid.uuid4()}.wav"
    filepath = os.path.join("static", filename)
    audio_file.save(filepath)

    # Convert and normalize
    sound = AudioSegment.from_file(filepath)
    sound = sound.set_channels(1).set_frame_rate(16000)
    sound.export(filepath, format="wav")

    # Transcribe with Whisper
    result = whisper_model.transcribe(filepath)
    os.remove(filepath)

    return jsonify({"text": result["text"]})

@app.route("/static/voice/<filename>")
def serve_voice(filename):
    return send_file(os.path.join(VOICE_DIR, filename), mimetype="audio/mpeg")

# ---------- MAIN ----------

if __name__ == '__main__':
    app.run(debug=True)
