import os
import glob
import subprocess

def count_files(directory):
    if not os.path.exists(directory):
        return 0
    # Only count files, not directories
    return len([name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name))])

def get_queue_status(pipeline_config):
    root = pipeline_config.root
    status = {}
    
    if pipeline_config.is_multistage:
        # Multistage: { stage: { queue_type: count } }
        for stage, queues in pipeline_config.queues.items():
            stage_status = {}
            for q_type, rel_path in queues.items():
                abs_path = os.path.join(root, rel_path)
                stage_status[q_type] = count_files(abs_path)
            status[stage] = stage_status
    else:
        # Single stage: { queue_name: count }
        # To make it compatible with multi-lane UI, maybe wrap in "default" stage?
        # Or let UI handle it. Let's return flat dict here and let API structure it.
        # Actually, let's wrap it in "Sync" stage for consistency if possible, 
        # or just return as is and have API/UI deduce.
        # Let's return { "Sync": { pending: ..., ... } } so frontend code is uniform?
        # Bandcamp queues are: pending, in_progress, failed, done.
        
        stage_status = {}
        for q_name, rel_path in pipeline_config.queues.items():
            abs_path = os.path.join(root, rel_path)
            stage_status[q_name] = count_files(abs_path)
        status["Sync"] = stage_status
        
    return status

def get_recent_logs(pipeline_config, lines=50):
    root = pipeline_config.root
    log_data = {}
    
    for pattern in pipeline_config.logs:
        full_pattern = os.path.join(root, pattern)
        files = glob.glob(full_pattern)
        for log_file in files:
            basename = os.path.basename(log_file)
            # Group by stage? MapGenerator logs are like Heightmap/logs/foo.log
            # We can use the parent dir as group name if we want.
            
            try:
                # Simple tail
                with open(log_file, 'r') as f:
                    # simplistic approach: read all, take last N lines
                    # for large files this is bad, but "boring code". 
                    # Optimization: seek to end and read backwards? 
                    # Or just run `tail` command?
                    # "Prefer boring, explicit code". `tail` command is robust.
                    
                    proc = subprocess.run(['tail', '-n', str(lines), log_file], capture_output=True, text=True)
                    content = proc.stdout
                    
                    log_data[basename] = content
            except Exception as e:
                log_data[basename] = f"Error reading log: {e}"
                
    return log_data
