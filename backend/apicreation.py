from flask import Flask, request, jsonify, send_file, send_from_directory
import soundfile as sf
import io
import base64
import os
import tempfile
import librosa
import numpy as np
import json
from datetime import datetime
from scipy.spatial.distance import cdist
from main import load_audio_features, get_all_audio_features, rank_similar_files
from pymongo import MongoClient
from flask_cors import CORS
import zipfile
from bson.objectid import ObjectId
import gridfs
import mimetypes


url = os.getenv('MONGODB_URI')
print("url", url)
client = MongoClient(url)
db = client['soundDB']

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)

# Store processed features globally
processed_features = {}


def validate_audio_file(file):
    """Validate uploaded audio file"""
    print(f"File received: {file.filename}, MIME type: {file.content_type}, Size: {len(file.read())}")
    
    # Check file size (e.g., max 10MB)
    if len(file.read()) > 10 * 1024 * 1024:
        return False, "File too large"
    file.seek(0)  # Reset file pointer
    
    # Check file extension
    allowed_extensions = {'.ogg', '.wav', '.mp3'}
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        return False, "Invalid file format"
    
    return True, None

@app.route('/search', methods=['POST'])
def search():
    """
    Search for similar sounds and return both rankings and files
    """
    temp_files = []  # Keep track of temp files to clean up

    try:
        # Validate that a file was uploaded
        print("request.files", request.files)
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        file = request.files['audio_file']

        valid, error = validate_audio_file(file)
        if not valid:
            print("file not valid")
            return jsonify({'error': error}), 400

        # Process uploaded file
        print("processing file")
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_files.append(temp_file.name)
            file.save(temp_file.name)
            reference_features = load_audio_features(temp_file.name)

        # Get all sounds from MongoDB
        sounds = db.demo_sounds.find()
        print("Retrieved sounds from MongoDB")
        print("sounds", sounds)
        # Extract features and filenames
        all_features = {}
        sound_titles = {}
        for i, sound in enumerate(sounds):
            embedding = sound['embedding']
            filename = sound['title']
            all_features[filename] = np.array(embedding)
            sound_titles[filename] = filename
        print(f"Extracted features and titles for {len(all_features)} sounds")
            
        if not all_features:
            print("No sounds found in database")
            return jsonify({'error': 'No sounds found in database'}), 400
        
        # Add reference file features
        reference_filename = file.filename
        all_features[reference_filename] = reference_features
        
        # Get rankings
        rankings = rank_similar_files(reference_filename, all_features)
        print(f"Generated rankings for {len(rankings)} files")
        
        # Format results with just rankings first
        ranked_sounds = []
        for filename, similarity in rankings:
            sound = db.demo_sounds.find_one({'title': filename})
            if sound:
                ranked_sounds.append({
                    'filename': filename,
                    'similarity': 1 - similarity,
                    'file_id': str(sound['file_id'])
                })

        # Return just the rankings if there's an issue with file creation
        if not ranked_sounds:
            return jsonify({'error': 'No matches found'}), 404

        try:
            # Create a ZIP file containing all ranked files
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                temp_files.append(temp_zip.name)
                with zipfile.ZipFile(temp_zip.name, 'w') as zf:
                    fs = gridfs.GridFS(db)
                    
                    for sound in ranked_sounds:
                        try:
                            audio_file = fs.get(ObjectId(sound['file_id']))
                            if audio_file:
                                zf.writestr(sound['filename'], audio_file.read())
                        except Exception as e:
                            print(f"Error adding file {sound['filename']}: {str(e)}")
                            continue

                    zf.writestr('rankings.json', json.dumps({'ranked_sounds': ranked_sounds}))

                # Send response
                response = send_file(
                    temp_zip.name,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name='search_results.zip'
                )

                # Add rankings to header
                rankings_json = base64.b64encode(json.dumps({'ranked_sounds': ranked_sounds}).encode()).decode()
                response.headers['X-Rankings-Data'] = rankings_json
                response.headers['Access-Control-Expose-Headers'] = 'X-Rankings-Data'

                # Clean up temp files after response is sent
                @response.call_on_close
                def cleanup():
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.unlink(temp_file)
                        except Exception as e:
                            print(f"Error cleaning up temp file {temp_file}: {str(e)}")

                return response

        except Exception as e:
            print(f"Error creating ZIP file: {str(e)}")
            # If ZIP creation fails, at least return the rankings
            return jsonify({'ranked_sounds': ranked_sounds})

    except Exception as e:
        # Clean up temp files if there's an error THIS MIGHT NEED TO BE REMOVED FROM HERE *****
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file {temp_file}: {str(cleanup_error)}")
        # TO HERE *****
        print(f"Error in search endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='localhost', port=3002, debug=True)