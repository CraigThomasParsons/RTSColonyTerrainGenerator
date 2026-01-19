import subprocess
import shlex

def get_systemd_status(pipeline_config):
    if not pipeline_config.systemd:
        return {}
    
    units = pipeline_config.systemd.get('units', [])
    user_mode = pipeline_config.systemd.get('user', False)
    
    status_map = {}
    
    cmd_base = ['systemctl']
    if user_mode:
        cmd_base.append('--user')
    
    cmd_base.append('is-active')
    
    # We can check multiple units at once? 
    # systemctl is-active unit1 unit2 ...
    # It prints status one per line.
    
    if not units:
        return {}
        
    cmd = cmd_base + units
    
    try:
        # check=False because is-active returns non-zero if inactive
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output_lines = result.stdout.strip().split('\n')
        
        for i, unit in enumerate(units):
            if i < len(output_lines):
                status_map[unit] = output_lines[i]
            else:
                status_map[unit] = "unknown"
                
    except Exception as e:
        for unit in units:
            status_map[unit] = f"error: {e}"
            
    return status_map
