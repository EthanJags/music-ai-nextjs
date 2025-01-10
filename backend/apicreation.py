from flask import Flask, request, jsonify
import soundfile as sf
import io
import base64
import os
import tempfile
import librosa
import numpy as np
from datetime import datetime
from scipy.spatial.distance import cdist
from main import load_audio_features, get_all_audio_features, rank_similar_files
from pymongo import MongoClient
from flask_cors import CORS

url = os.getenv('MONGODB_URI')
print("url", url)
client = MongoClient(url)
db = client['soundDB']

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],  # Your frontend URL
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

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
    Search for similar sounds in MongoDB
    """
    try:
        # Validate that a file was uploaded
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        file = request.files['audio_file']

        valid, error = validate_audio_file(file)
        if not valid:
            return jsonify({'error': error}), 400

        # Create temporary file to process the upload
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            file.save(temp_file.name)
            reference_features = load_audio_features(temp_file.name)
        
        # Get features for uploaded file
        reference_features = load_audio_features(temp_file.name)
        os.unlink(temp_file.name)
        
        # Get all sounds from MongoDB
        sounds = db.demo_sounds.find()
        print("Retrieved sounds from MongoDB")
        
        # Extract features and filenames
        all_features = {}
        sound_titles = {}
        for sound in sounds:
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
        
        # Format results with titles
        ranked_sounds = []
        for filename, similarity in rankings:
            ranked_sounds.append({
                'filename': filename,
                'similarity': 1 - similarity
            })
        print(f"Formatted results for {len(ranked_sounds)} sounds")
        
        return jsonify({
            'ranked_sounds': ranked_sounds
        })
        
    except Exception as e:
        print(f"Error in analyze endpoint: {str(e)}")
        print(f"Request: {request.json}")
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


if __name__ == '__main__':
    app.run(host='localhost', port=3002, debug=True)