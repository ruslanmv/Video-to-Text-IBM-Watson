from flask import Flask, request, jsonify, render_template
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import os
from dotenv import load_dotenv
import mimetypes
from moviepy.editor import VideoFileClip
from werkzeug.utils import secure_filename

load_dotenv()

authenticator = IAMAuthenticator(os.getenv("API_KEY"))
speech_to_text = SpeechToTextV1(authenticator=authenticator)
speech_to_text.set_service_url(os.getenv("SERVICE_URL"))

app = Flask(__name__)

# Create the "uploads" directory if it doesn't exist
current_directory = os.getcwd()
uploads_directory = os.path.join(current_directory, 'uploads')
if not os.path.exists(uploads_directory):
    os.makedirs(uploads_directory)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert_video_to_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    video_file = request.files['file']
    file_name = video_file.filename
    content_type, _ = mimetypes.guess_type(file_name)

    if content_type not in ['video/mp4', 'video/quicktime']:
        return jsonify({'error': 'Invalid file format. Only MP4 and MOV videos are supported.'}), 400

    # Save the file
    file_path = os.path.join('uploads', secure_filename(file_name))
    video_file.save(file_path)
    print(f"File saved at: {file_path}")
    audio_path = 'audio.mp3'

    try:
        video = VideoFileClip(file_path)
        audio = video.audio
        audio.write_audiofile(audio_path, codec='libmp3lame')
        
        # Close the opened files
        audio.close()
        video.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    with open(audio_path, 'rb') as audio_file:
        response = speech_to_text.recognize(audio=audio_file,
                                            content_type='audio/mp3',
                                            speaker_labels=True,
                                            inactivity_timeout=-1).get_result()

    transcripts = [result['alternatives'][0]['transcript'] for result in response['results']]
    transcript = " ".join(x for x in transcripts)

    # Close the opened files
    audio_file.close()

    os.remove(file_path)
    os.remove(audio_path)

    return jsonify({'transcript': transcript})


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)