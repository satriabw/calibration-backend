# Calibration Backend

Flask + SQLite backend for calibration management system. Based on https://github.com/satriabw/monocular-calibration

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

The server will start on `http://localhost:8000`

## API Endpoints

### Calibrations

- `GET /api/calibrations` - Get all calibrations
- `GET /api/calibrations/<id>` - Get calibration by ID
- `POST /api/calibrations` - Create new calibration
- `PUT /api/calibrations/<id>` - Update calibration
- `DELETE /api/calibrations/<id>` - Soft delete calibration

### Calibration Versions

- `GET /api/calibration-versions` - Get all calibration versions
- `GET /api/calibration-versions/<id>` - Get calibration version by ID
- `POST /api/calibration-versions` - Create new calibration version
- `PUT /api/calibration-versions/<id>` - Update calibration version
- `DELETE /api/calibration-versions/<id>` - Soft delete calibration version

### Background Processing (for frontend)

- `POST /api/session/start` - Start processing session
- `GET /api/background/<session_id>/latest` - Get latest processed frame
- `POST /api/background/<session_id>/save` - Save background

## Database Schema

### calibration table
- id (Integer, Primary Key)
- name (String, Not Null)
- version_id (Integer, Foreign Key to calibration_version.id)
- created_at (DateTime)
- updated_at (DateTime)
- deleted_at (DateTime, Nullable)

### calibration_version table
- id (Integer, Primary Key)
- file (Text, Not Null) - File path or base64 data
- created_at (DateTime)
- updated_at (DateTime)
- deleted_at (DateTime, Nullable)

## Features

- **Soft Delete**: Records are marked as deleted instead of being removed
- **Timestamps**: Automatic created_at and updated_at timestamps
- **Relationships**: Foreign key relationship between calibration and calibration_version
- **CORS**: Cross-origin requests enabled for frontend integration
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## Example Usage

### Create a calibration version:
```bash
curl -X POST http://localhost:8000/api/calibration-versions \
  -H "Content-Type: application/json" \
  -d '{"file": "/path/to/calibration/file.json"}'
```

### Create a calibration:
```bash
curl -X POST http://localhost:8000/api/calibrations \
  -H "Content-Type: application/json" \
  -d '{"name": "Camera Calibration 1", "version_id": 1}'
```

### Get all calibrations:
```bash
curl http://localhost:8000/api/calibrations
```
