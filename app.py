from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

from database import db
from routes import api_bp
from utils import register_socketio_events

import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///calibration.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)
CORS(app)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=True
)

register_socketio_events(socketio)
app.register_blueprint(api_bp, url_prefix='/api')

@app.route("/")
def home():
    return {}

@app.route('/health')
def health():
    return {'status': 'healthy'}

def create_tables():
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    # Create tables on startup
    create_tables()
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
