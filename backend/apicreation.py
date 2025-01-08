from backend.apicreation import Flask, request, jsonify
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

app = Flask(__name__)

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

@app.route('/initialize', methods=['POST'])
def initialize():
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

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Enhanced analysis endpoint with more options
    """
    try:
        if not processed_features:
            return jsonify({'error': 'No reference files initialized. Call /initialize first'}), 400
            
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        # Validate file
        is_valid, error_message = validate_audio_file(file)
        if not is_valid:
            return jsonify({'error': error_message}), 400
            
        # Get analysis parameters
        threshold = float(request.args.get('threshold', 0.8))
        limit = int(request.args.get('limit', 10))
        metric = request.args.get('metric', 'cosine')
            
        # Create temporary file for upload
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_file.name)
        
        # Extract features
        features = load_audio_features(temp_file.name)
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        # Add uploaded file features
        all_features = processed_features.copy()
        all_features['input.ogg'] = features
        
        # Get rankings
        start_time = datetime.now()
        rankings = rank_similar_files('input.ogg', all_features)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Filter results
        rankings = [r for r in rankings if (1 - r[1]) >= threshold][:limit]
        
        return jsonify({
            'similar_files': rankings,
            'analysis_time': processing_time,
            'input_features': features.tolist(),
            'threshold': threshold,
            'metric': metric
        })
        
    except Exception as e:
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
    
@app.route('/reference-files', methods=['GET'])
def get_reference_files():
    """
    Get list of all reference files and their metadata
    Returns: {
        "files": [
            {
                "filename": "sound1.ogg",
                "duration": "2.5s", 
                "added_date": "2024-03-20",
                # Could include other metadata like tags, categories, etc.
            },
            ...
        ]
    }
    """
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
    app.run(host='0.0.0.0', port=5000, debug=True)