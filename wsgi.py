import os
import sys
from flask import Flask
from flask_cors import CORS

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from scrappyflask.scrapflask.database import db
from scrappyflask.scrapflask.config import Config
from scrappyflask.scrapflask.routes import bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        from scrappyflask.scrapflask import models
        db.create_all()
        app.register_blueprint(bp)
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)