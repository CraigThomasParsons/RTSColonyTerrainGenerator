import yaml
import os

class PipelineConfig:
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.root = data.get('root')
        self.queues = data.get('queues', {})
        self.logs = data.get('logs', [])
        self.systemd = data.get('systemd', {})
        self.job = data.get('job', {})

    @property
    def is_multistage(self):
        # Heuristic: if the first value in queues is a dict, it's multistage
        if not self.queues:
            return False
        first_val = next(iter(self.queues.values()))
        return isinstance(first_val, dict)

    def get_stages(self):
        if self.is_multistage:
            return list(self.queues.keys())
        return ["default"]

def load_pipeline(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Pipeline config not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    return PipelineConfig(data)

def list_pipelines(pipelines_dir):
    pipelines = []
    if os.path.exists(pipelines_dir):
        for filename in os.listdir(pipelines_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                path = os.path.join(pipelines_dir, filename)
                try:
                    p = load_pipeline(path)
                    pipelines.append({
                        'id': p.id,
                        'name': p.name,
                        'path': path
                    })
                except Exception as e:
                    print(f"Error loading {path}: {e}")
    return pipelines
