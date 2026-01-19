from flask import Flask, jsonify, request, send_from_directory
import argparse
import os
import sys

# Add current directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pipeline_loader
import fs_observer
import systemd_observer

app = Flask(__name__)

# Global state
current_pipeline = None
pipelines_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pipelines')

@app.route('/')
def index():
    return send_from_directory('../ui', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../ui', path)

@app.route('/api/config')
def get_config():
    if not current_pipeline:
        return jsonify({'error': 'No pipeline loaded'}), 500
    
    return jsonify({
        'id': current_pipeline.id,
        'name': current_pipeline.name,
        'root': current_pipeline.root,
        'is_multistage': current_pipeline.is_multistage,
        'stages': current_pipeline.get_stages(),
        'systemd_units': current_pipeline.systemd.get('units', [])
    })

@app.route('/api/queues')
def get_queues():
    if not current_pipeline:
        return jsonify({})
    return jsonify(fs_observer.get_queue_status(current_pipeline))

@app.route('/api/systemd')
def get_systemd():
    if not current_pipeline:
        return jsonify({})
    return jsonify(systemd_observer.get_systemd_status(current_pipeline))

@app.route('/api/logs')
def get_logs():
    if not current_pipeline:
        return jsonify({})
    return jsonify(fs_observer.get_recent_logs(current_pipeline))

@app.route('/api/pipelines', methods=['GET'])
def list_avail_pipelines():
    return jsonify(pipeline_loader.list_pipelines(pipelines_dir))

@app.route('/api/pipeline/switch', methods=['POST'])
def switch_pipeline():
    global current_pipeline
    data = request.json
    path = data.get('path')
    if not path:
        return jsonify({'error': 'Path required'}), 400
    
    try:
        current_pipeline = pipeline_loader.load_pipeline(path)
        return jsonify({'success': True, 'name': current_pipeline.name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline Dashboard')
    parser.add_argument('--config', help='Path to pipeline config yaml')
    parser.add_argument('--port', type=int, default=5001, help='Port to run on')
    
    args = parser.parse_args()
    
    # Try to load config
    if args.config:
        try:
            current_pipeline = pipeline_loader.load_pipeline(args.config)
            print(f"Loaded pipeline: {current_pipeline.name}")
        except Exception as e:
            print(f"Failed to load config {args.config}: {e}")
            sys.exit(1)
    else:
        # Try to find mapgenerator default, then bandcamp, or just first one
        avail = pipeline_loader.list_pipelines(pipelines_dir)
        if avail:
            # Prefer mapgenerator for this deliverable
            found = next((p for p in avail if 'mapgenerator' in p['path']), None)
            if not found:
                found = avail[0]
            
            print(f"No config specified, defaulting to {found['path']}")
            current_pipeline = pipeline_loader.load_pipeline(found['path'])
        else:
            print("No pipelines found in pipelines/ directory.")
            # We fail but maybe start anyway so UI can show empty? 
            # Nah let's just warn.
            
    print(f"Starting server on port {args.port}...")
    app.run(host='0.0.0.0', port=args.port)
