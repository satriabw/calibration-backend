> # Calibration Backend
> 
> Flask + Socket.IO + SQLite backend for monocular camera calibration management system. Based on https://github.com/satriabw/monocular-calibration
> 
> ## Features
> 
> - **Real-time Background Extraction**: WebSocket-based frame processing for background extraction from camera/video
> - **Camera Calibration**: Monocular camera calibration using point correspondences
> - **Version Management**: Automatic versioning with active/inactive status management
> - **Soft Delete**: Records are marked as deleted instead of being removed
> - **CORS Enabled**: Cross-origin requests enabled for frontend integration
> 
> ## Setup
> 
> 1. **Install Python dependencies:**
>    ```bash
>    pip install -r requirements.txt
>    ```
> 
> 2. **Set up environment variables:**
>    Create a `.env` file in the root directory:
>    ```env
>    SECRET_KEY=your-secret-key
>    DATABASE_URL=sqlite:///calibration.db
>    PORT=8000
>    FLASK_DEBUG=False
>    ```
> 
> 3. **Run the application:**
>    ```bash
>    python app.py
>    ```
> 
> The server will start on `http://localhost:8000`
> 
> ## API Documentation
> 
> ### REST API Endpoints
> 
> #### Calibration
> 
> **`POST /api/calibrate`**
> 
> Perform camera calibration and save the result.
> 
> **Request Body:**
> ```json
> {
>   "name": "test_calibration",
>   "image": "data:image/jpeg;base64,...",
>   "pixels": [[x1, y1], [x2, y2], ...],
>   "coordinates": [[lat1, lng1], [lat2, lng2], ...],
>   "origin": [origin_lat, origin_lng]
> }
> ```
> 
> **Response:**
> ```json
> {
>   "calibrations": [
>     {
>       "id": 4,
>       "name": "test_calibration",
>       "version_id": 4,
>       "file_name": "./artifacts/camera_model_4.yml",
>       "status": "active",
>       "created_at": "2025-11-24T14:07:31.899759",
>       "updated_at": "2025-11-24T14:07:31.899762",
>       "deleted_at": null
>     }
>   ],
>   "rms_error": 2.2304948066746833,
>   "visualization_image": "data:image/png;base64,..."
> }
> ```
> 
> **Notes:**
> - Previous active version is automatically set to inactive
> - Version ID is auto-incremented
> - Returns all calibration versions for the given name
> - Visualization image shows the calibration result
> 
> #### Health Check
> 
> **`GET /health`**
> 
> Check server health status.
> 
> **Response:**
> ```json
> {
>   "status": "healthy"
> }
> ```
> 
> ### WebSocket Events
> 
> The server uses Socket.IO for real-time background processing.
> 
> #### Client → Server Events
> 
> **`connect`**
> - Automatically triggered on connection
> - No data required
> 
> **`start_session`**
> ```json
> {
>   "input_mode": "camera" | "file"
> }
> ```
> - Starts a new background processing session
> - Returns: `session_started` event
> 
> **`process_frame`**
> ```json
> {
>   "frame": "data:image/jpeg;base64,..."
> }
> ```
> - Process a single frame for background extraction
> - Returns: `frame_processed` event
> 
> **`save_background`**
> ```json
> {}
> ```
> - Save the extracted background image
> - Returns: `background_saved` event
> 
> **`update_background`**
> ```json
> {
>   "frame": "data:image/jpeg;base64,..."
> }
> ```
> - Manually update background with a specific frame
> - Returns: `background_updated` event
> 
> **`end_session`**
> ```json
> {
>   "session_id": "session-id"
> }
> ```
> - End the current session and clean up
> - Returns: `session_ended` event
> 
> **`disconnect`**
> - Automatically triggered on disconnection
> - Cleans up active sessions
> 
> #### Server → Client Events
> 
> **`connected`**
> ```json
> {
>   "message": "Connected to background processing server"
> }
> ```
> 
> **`session_started`**
> ```json
> {
>   "success": true,
>   "session_id": "uuid-v4"
> }
> ```
> 
> **`frame_processed`**
> ```json
> {
>   "success": true,
>   "session_id": "uuid-v4",
>   "frame_count": 10,
>   "processed_frame": "data:image/jpeg;base64,...",
>   "status": "",
>   "has_background": true
> }
> ```
> 
> **`background_saved`**
> ```json
> {
>   "success": true,
>   "session_id": "uuid-v4",
>   "message": "Background saved successfully",
>   "background_image": "data:image/jpeg;base64,...",
>   "metadata": {
>     "width": 640,
>     "height": 480,
>     "frame_count": 10
>   }
> }
> ```
> 
> **`background_updated`**
> ```json
> {
>   "success": true,
>   "message": "Background updated successfully"
> }
> ```
> 
> **`session_ended`**
> ```json
> {
>   "success": true,
>   "message": "Session ended successfully"
> }
> ```
> 
> **`error`**
> ```json
> {
>   "message": "Error description"
> }
> ```
> 
> ## Database Schema
> 
> ### `calibration` Table
> 
> | Column      | Type     | Description                                    |
> |-------------|----------|------------------------------------------------|
> | id          | Integer  | Primary Key                                    |
> | name        | String   | Calibration name (Not Null)                    |
> | version_id  | Integer  | Version number                                 |
> | file_name   | Text     | Path to camera model YAML file (Not Null)      |
> | status      | String   | 'active' or 'inactive' (default: 'active')     |
> | created_at  | DateTime | Timestamp of creation                          |
> | updated_at  | DateTime | Timestamp of last update                       |
> | deleted_at  | DateTime | Timestamp of soft deletion (Nullable)          |
> 
> ## Workflow
> 
> ### Background Extraction Workflow
> 
> 1. Client connects to WebSocket
> 2. Client emits `start_session` with input mode
> 3. Client sends frames via `process_frame` events (recommended 1 FPS)
> 4. Server processes frames using running average for background extraction
> 5. Server returns processed background via `frame_processed` events
> 6. Client emits `save_background` to save the final background
> 7. Client receives background image and metadata via `background_saved`
> 8. Client emits `end_session` to clean up
> 
> ### Calibration Workflow
> 
> 1. Client has background image and user-selected point correspondences
> 2. Client sends calibration data to `POST /api/calibrate`
> 3. Server performs camera calibration using monocular-calibration library
> 4. Server saves calibration to YAML file in `./artifacts/`
> 5. Server creates database record with auto-incremented version
> 6. Server sets previous version to inactive
> 7. Server returns all calibration versions, RMS error, and visualization
> 
> ## Error Handling
> 
> The API uses standard HTTP status codes:
> - `200 OK` - Successful request
> - `400 Bad Request` - Missing required parameters or invalid data
> - `404 Not Found` - Resource not found
> - `500 Internal Server Error` - Server error
> 
> WebSocket errors are emitted via the `error` event with descriptive messages.
> 
> ## Development
> 
> ### Project Structure
> ```
> calibration-backend/
> ├── app.py              # Main application entry point
> ├── routes.py           # REST API routes
> ├── models.py           # Database models
> ├── database.py         # Database configuration
> ├── utils/
> │   ├── __init__.py
> │   ├── sockets.py      # WebSocket event handlers
> │   ├── background.py   # Background processing logic
> │   └── calibration.py  # Camera calibration logic
> ├── artifacts/          # Saved calibration files
> └── instance/           # SQLite database
> ```
> EOF