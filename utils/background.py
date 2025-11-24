import base64
import cv2
import numpy as np

def _read_base64_image(frame_data):
    if ',' in frame_data:
        frame_data = frame_data.split(',')[1]
    
    img_data = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise ValueError("Decoded frame is None")
    
    return frame

def process_frame_background(frame_data, session):
        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]
        
        frame = _read_base64_image(frame_data)
        
        session['frame_count'] += 1
        
        if session['background'] is None:
            session['background'] = frame.astype(np.float32)
            processed = np.zeros_like(frame)
        else:
            # Accumulate weighted average for background
            frame_float = frame.astype(np.float32)
            cv2.accumulateWeighted(frame_float, session['background'], 0.1)
            
            # Convert accumulated background to uint8 for display
            processed = cv2.convertScaleAbs(session['background'])
            
        # Encode processed frame to base64
        _, buffer = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, 85])
        processed_base64 = base64.b64encode(buffer).decode('utf-8')

        return processed_base64

def update_background(frame_data, session):
    frame = _read_base64_image(frame_data)
    session['background'] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

def get_base64_image(frame):
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode('utf-8')
