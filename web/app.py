import os
import sys

# Set up Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import after path setup
from flask import Flask
from flask_cors import CORS
from web.database import db
from web.config import Config

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        from . import models
        db.create_all()
        from .routes import bp
        app.register_blueprint(bp)
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)