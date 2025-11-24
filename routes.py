import base64
from flask import Blueprint, request, jsonify
import cv2

from utils import calibrate
from models import Calibration

api_bp = Blueprint('api', __name__)
active_sessions = {} 

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/calibrate', methods=['POST'])
def calibrate_route():
    data = request.json
    image = data.get('image')
    pixels = data.get('pixels')
    coordinates = data.get('coordinates')
    name  = data.get('name')
    origin = data.get('origin')

    if not image or not pixels or not coordinates or not origin or not name:
        return bad_request("Missing required parameters")

    try:
        # Get the latest version and increment
        calibration = Calibration.get_latest_active_version()
        version = 1
        if calibration:
            version = calibration.version_id + 1
        
        # Calibrate the camera and save to database
        camera_model_path, rms, image_viz = calibrate(
            image, pixels, coordinates, origin, version
        )
        Calibration.create(name=name, version_id=version, file_name=camera_model_path)
        
        # Build the response
        image_viz_b64 = "data:image/png;base64," + base64.b64encode(
            cv2.imencode('.png', image_viz)[1]
        ).decode('utf-8')
        calibrations = Calibration.get_calibration_by_name(name)

        response = {
            'calibrations': [calib.to_dict() for calib in calibrations] if calibrations else None,
            'rms_error': rms,
            'visualization_image': image_viz_b64
        }
        return jsonify(response), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return internal_error(str(e))
