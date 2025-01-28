
import os
import shutil
from datetime import datetime, timedelta

def cleanup_old_sessions(base_output_folder, max_age_hours=24):
    """Remove session folders older than specified hours."""
    now = datetime.now()
    
    for session_id in os.listdir(base_output_folder):
        session_path = os.path.join(base_output_folder, session_id)
        if os.path.isdir(session_path) and session_id != "pdfs":
            created_time = datetime.fromtimestamp(os.path.getctime(session_path))
            if now - created_time > timedelta(hours=max_age_hours):
                shutil.rmtree(session_path)
