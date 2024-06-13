from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
from cachetools import TTLCache
import aiohttp
import asyncio
import re

# Define the class hierarchy
class_hierarchy = {
    'Fire': ['Airblow', 'Blast', 'Cracklings', 'Cracks', 'Deep combustion', 'Explosion', 'Flames', 'Ignition', 'Sharp combustion', 'Spark', 'Volcano-eruption'],
    'Water': ['Boiling', 'Dive', 'Freeze', 'Pouring', 'Rain-flow-heavy', 'Rain-flow-light', 'Rain-flow-medium', 'Splash'],
    'Air': ['Pressure-long', 'Pressure-med', 'Pressure-short', 'Vapour', 'Whoosh-grainy-long', 'Whoosh-grainy-med', 'Whoosh-grainy-short', 'Whoosh-slick-long', 'Whoosh-slick-med', 'Whoosh-slick-short', 'Wind'],
    'Land': ['Cracking', 'Earthquake', 'Rockslide', 'Tremor'],
    'Electrical': ['Buzz', 'Electrocution', 'Shock-arcs', 'Spark', 'Thunderbolt-big', 'Thunderbolt-medium', 'Thunderbolt-small', 'Zap'],
    'Living': ['Breath', 'Chills', 'Heartbeat', 'Stabbing', 'Tachycardia', 'Wound', 'Footsteps'],
    'Materials': ['Breaking-glass', 'Collision-metal', 'Collision-plastic', 'Collision-rubber', 'Collision-wood', 'Friction-metal', 'Friction-plastic', 'Friction-rubber', 'Friction-wood'],
    'Mechanics': ['Alarm', 'Click-bouncy', 'Click-resonant', 'Click-rough', 'Engine', 'Pump', 'Rumble', 'Scratch', 'Translate', 'Zip', 'Wipers'],
    'Character': ['Biohazard', 'Disintegration', 'Energy-burst', 'Healing', 'Injured', 'Madness', 'Magic-spell', 'Materialisation', 'Poison', 'Teleportation', 'Time-freeze', 'Time-travel', 'Time-warp', 'Comet', 'Pulse', 'Sparkles'],
    'Interface': ['Buttons', 'Hover', 'Notifications', 'Scroll', 'Slider', 'Snap', 'Swipe'],
    'Weapons': ['Grenade', 'Knifes', 'Machinegun', 'Pistol', 'Rifles', 'Shotgun', 'Smgs', 'Sniper', 'Bullet']
}

# Extract main classes
main_classes = list(class_hierarchy.keys())

# Define the classes for position classification
position_classes = ["front", "back", "right", "left"]

# Define the Hugging Face API endpoint and API key
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
API_KEY = "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"  # Hugging Face API key

# Initialize Flask app
app = Flask(__name__)

#authentication key
AUTH_KEY = 'my_secret_auth_key'

# Directory containing the .wav files
AUDIO_DIR = "audio_files"


os.makedirs(AUDIO_DIR, exist_ok=True)

# Caching mechanism
cache = TTLCache(maxsize=100, ttl=300)

# Define the HTML template for the interactive interface
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Text to Haptics</title>
</head>
<body>
    <h1>Text to Haptics</h1>
    <form id="classify-form">
        <label for="text">Enter text:</label><br><br>
        <input type="text" id="text" name="text" size="50"><br><br>
        <input type="submit" value="Classify">
    </form>
    <h2>Result:</h2>
    <p id="result"></p>
    <audio id="audio-player" controls></audio>
    <script>
        document.getElementById('classify-form').onsubmit = async function(event) {
            event.preventDefault();
            const text = document.getElementById('text').value;
            const response = await fetch('/classify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': '{{ auth_key }}'
                },
                body: JSON.stringify({ text: text })
            });
            const result = await response.json();
            const resultElement = document.getElementById('result');
            const audioPlayer = document.getElementById('audio-player');
            
            if (result.main_class && result.sub_class && result.position) {
                resultElement.innerText = `Main Class: ${result.main_class}, Subclass: ${result.sub_class}, Position: ${result.position}, First Position: ${result.first_position}, Second Position: ${result.second_position}`;
                audioPlayer.src = `/audio/${result.sub_class}.wav`;
                audioPlayer.play();
                console.log(`Classified as: ${result.main_class}, Subclass: ${result.sub_class}, Position: ${result.position}, First Position: ${result.first_position}, Second Position: ${result.second_position}`);
            } else {
                resultElement.innerText = `Error: ${result.error}`;
                audioPlayer.src = '';
            }
        }
    </script>
</body>
</html>
"""

# Function to classify text using Hugging Face API
async def classify_text(session, text, candidate_labels):
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": candidate_labels
        }
    }
    async with session.post(API_URL, headers=headers, json=payload) as response:
        if response.status == 200:
            result = await response.json()
            predicted_class = result['labels'][0]
            return predicted_class, result['scores'][0]
        else:
            raise Exception(f"API request failed with status code {response.status}: {await response.text()}")

# Function to classify text in chunks
async def classify_text_in_chunks(session, text, candidate_labels):
    best_class = None
    best_score = -1
    chunk_size = 10
    for i in range(0, len(candidate_labels), chunk_size):
        chunk = candidate_labels[i:i+chunk_size]
        predicted_class, score = await classify_text(session, text, chunk)
        if score > best_score:
            best_score = score
            best_class = predicted_class
    return best_class

# Function to preprocess text
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text

# Function to extract positions based on keywords
def extract_positions(text):
    pattern = re.compile(r'\b(front|back|left|right|top|bottom)\b')
    positions = pattern.findall(text)
    return positions

# Function to determine the first and second positions
def determine_positions(positions):
    if len(positions) >= 2:
        first_position = positions[0]
        second_position = positions[1]
    else:
        first_position = None
        second_position = None
    return first_position, second_position

# Serve the HTML interface
@app.route('/')
def index():
    return render_template_string(html_template, auth_key=AUTH_KEY)

# Define the API endpoint
@app.route('/classify', methods=['POST'])
async def classify():
    auth_key = request.headers.get('Authorization')
    if auth_key != AUTH_KEY:
        return jsonify({'error': 'Unauthorized access'}), 401

    data = request.get_json()  # Synchronous method, no await
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    cache_key = text
    if cache_key in cache:
        return jsonify(cache[cache_key])

    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Classify the main class
            main_class = await classify_text_in_chunks(session, text, main_classes)
            
            # Step 2: Classify the subclass within the determined main class
            sub_class_candidates = class_hierarchy[main_class]
            sub_class = await classify_text_in_chunks(session, text, sub_class_candidates)

            # Step 3: Determine position
            position = await classify_text_in_chunks(session, text, position_classes)

            # Step 4: Detect transitions
            preprocessed_text = preprocess_text(text)
            positions = extract_positions(preprocessed_text)
            first_position, second_position = determine_positions(positions)

            result = {
                'main_class': main_class,
                'sub_class': sub_class,
                'position': position,
                'first_position': first_position,
                'second_position': second_position
            }
            cache[cache_key] = result
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Serve audio files
@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
