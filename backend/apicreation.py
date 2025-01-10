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
    # Check file size (e.g., max 10MB)
    if len(file.read()) > 10 * 1024 * 1024:
        return False, "File too large"
    file.seek(0)  # Reset file pointer
    
    # Check file extension
    allowed_extensions = {'.ogg', '.wav', '.mp3'}
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        return False, "Invalid file format"
    
    return True, None

@app.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'reference_files': len(processed_features),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/reference-files', methods=['GET'])
def get_reference_files():
    """Get list of all reference files and their metadata"""
    try:
        files = []
        for filename in processed_features.keys():
            # Get basic file info
            file_path = os.path.join(request.json.get('directory', ''), filename)
            if os.path.exists(file_path):
                y, sr = librosa.load(file_path)
                duration = librosa.get_duration(y=y, sr=sr)
                files.append({
                    'filename': filename,
                    'duration': f"{duration:.2f}s",
                    'added_date': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                })
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    """
    Enhanced initialization endpoint with more options
    """
    try:
        data = request.json
        directories = data.get('directories', [data.get('directory')])
        
        if not directories:
            return jsonify({'error': 'No directories provided'}), 400
            
        # Validate directories
        for directory in directories:
            if not os.path.isdir(directory):
                return jsonify({'error': f'Invalid directory path: {directory}'}), 400
        
        # Processing options
        options = {
            'n_mfcc': data.get('n_mfcc', 13),
            'normalize': data.get('normalize', True),
            'file_types': data.get('file_types', ['.ogg', '.wav', '.mp3'])
        }
            
        # Process all audio files in directories
        global processed_features
        processed_features = {}
        for directory in directories:
            features = get_all_audio_features(directory)
            processed_features.update(features)
        
        return jsonify({
            'message': 'Successfully processed reference files',
            'num_files': len(processed_features),
            'directories': directories
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            return jsonify({'error': error}), 400

        # Process uploaded file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_files.append(temp_file.name)
            file.save(temp_file.name)
            reference_features = load_audio_features(temp_file.name)

        # Get all sounds from MongoDB
        sounds = db.demo_sounds.find()
        print("Retrieved sounds from MongoDB")
        
        # Extract features and filenames
        all_features = {}
        sound_titles = {}
        for i, sound in enumerate(sounds):
            embedding = sound['embedding']
            filename = sound['title']
            print("filename", filename)
            print(f"Processing sound {i+1} of {len(sounds)}")
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

@app.route('/batch-analyze', methods=['POST'])
def batch_analyze():
    """Analyze multiple files at once"""
    try:
        if not processed_features:
            return jsonify({'error': 'No reference files initialized'}), 400
            
        if 'audio_files' not in request.files:
            return jsonify({'error': 'No audio files provided'}), 400
            
        files = request.files.getlist('audio_files')
        if not files:
            return jsonify({'error': 'No files selected'}), 400
            
        results = []
        for file in files:
            # Process each file similarly to /analyze endpoint
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            file.save(temp_file.name)
            
            features = load_audio_features(temp_file.name)
            os.unlink(temp_file.name)
            
            all_features = processed_features.copy()
            all_features[file.filename] = features
            
            rankings = rank_similar_files(file.filename, all_features)
            
            results.append({
                'filename': file.filename,
                'similar_files': rankings[:10]  # Top 10 matches
            })
            
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        return jsonify({
            'total_reference_files': len(processed_features),
            'feature_dimensions': next(iter(processed_features.values())).shape[0] if processed_features else 0,
            'last_initialized': datetime.fromtimestamp(
                os.path.getctime(request.json.get('directory', ''))
            ).isoformat() if processed_features else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reference-files/<filename>', methods=['GET']) 
def get_reference_file_details(filename):
    """
    Get detailed information about a specific reference file
    Returns features, metadata, and similar files within the reference set
    """
    try:
        if filename not in processed_features:
            return jsonify({'error': 'File not found'}), 404
            
        file_path = os.path.join(request.json.get('directory', ''), filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on disk'}), 404
            
        # Get audio metadata
        y, sr = librosa.load(file_path)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Get similar files
        rankings = rank_similar_files(filename, processed_features)
        
        return jsonify({
            'filename': filename,
            'duration': f"{duration:.2f}s",
            'added_date': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
            'features': processed_features[filename].tolist(),
            'similar_files': rankings[:10]  # Top 10 similar files
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reference-files', methods=['POST'])
def add_reference_file():
    """
    Add a new file to the reference set
    Should trigger feature extraction and update the processed_features
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        # Validate file
        valid, error = validate_audio_file(file)
        if not valid:
            return jsonify({'error': error}), 400
            
        # Save file temporarily and extract features
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_file.name)
        
        features = load_audio_features(temp_file.name)
        os.unlink(temp_file.name)
        
        # Add to processed features
        processed_features[file.filename] = features
        
        return jsonify({
            'message': 'File added successfully',
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reference-files/<filename>', methods=['DELETE'])
def remove_reference_file(filename):
    """Remove a file from the reference set"""
    try:
        if filename not in processed_features:
            return jsonify({'error': 'File not found'}), 404
            
        del processed_features[filename]
        return jsonify({
            'message': 'File removed successfully',
            'filename': filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_mime_type(filename):
    """Detect mime type of file"""
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        directory = 'path/to/your/files'
        file_path = os.path.join(directory, filename)
        
        # Validate file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Get file size for progress tracking
        file_size = os.path.getsize(file_path)
        
        response = send_file(
            file_path,
            mimetype=get_mime_type(filename),
            as_attachment=True
        )
        
        # Add headers for better download handling
        response.headers['Content-Length'] = file_size
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Accept-Ranges'] = 'bytes'
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=3002, debug=True)