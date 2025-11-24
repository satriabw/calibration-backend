from flask_socketio import emit
from flask import request
from datetime import datetime
from .background import process_frame_background, update_background, get_base64_image

import base64
import numpy as np
import cv2
import uuid
import logging

active_sessions = {}
logger = logging.getLogger(__name__)

def register_socketio_events(socketio):
    def validate_and_get_session(sid):
        if sid not in active_sessions:
            raise ValueError("No active session for this client")
        
        return active_sessions[sid]
    
    def validate_and_get_frame(data):
        frame_data = data.get('frame')
        if not frame_data:
            raise ValueError("No frame data provided")
        
        return frame_data
    
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to background processing server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")
        if request.sid in active_sessions:
            del active_sessions[request.sid]
            logger.info(f"Session cleaned up for {request.sid}")
    
    @socketio.on('start_session')
    def handle_start_session(data):
        session_id = str(uuid.uuid4())
        
        active_sessions[request.sid] = {
            'session_id': session_id,
            'frame_count': 0,
            'background': None,
            'created_at': datetime.now(),
            'input_mode': data.get('input_mode', 'camera'),
            'saved_background': None
        }
        
        logger.info(f"Started session {session_id} for client {request.sid}")
        emit('session_started', {
            'success': True,
            'session_id': session_id
        })
    
    @socketio.on('process_frame')
    def handle_process_frame(data):
        """Process a single frame from the client"""
        try:
            session = validate_and_get_session(request.sid)
            frame_data = validate_and_get_frame(data)
            processed_base64 = process_frame_background(frame_data, session)

            emit('frame_processed', {
                'success': True,
                'session_id': session['session_id'],
                'frame_count': session['frame_count'],
                'processed_frame': f'data:image/jpeg;base64,{processed_base64}',
                'status': '',
                'has_background': session['background'] is not None
            })
            
        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            emit('error', {'message': f'Frame processing error: {str(e)}'})
        
    @socketio.on('save_background')
    def handle_save_background(data):
        """Save the current background"""
        try:
            session = validate_and_get_session(request.sid)
            
            if session['background'] is None:
                emit('error', {'message': 'No background captured yet'})
                return
            
            background_base64 = get_base64_image(session['background'])
            emit('background_saved', {
                'success': True,
                'session_id': session['session_id'],
                'message': 'Background saved successfully',
                'background_image': f'data:image/jpeg;base64,{background_base64}',
                'metadata': {
                    'width': int(session['background'].shape[1]),
                    'height': int(session['background'].shape[0]),
                    'frame_count': session['frame_count']
                }
        })
            
        except Exception as e:
            logger.error(f"Error saving background: {str(e)}")
            emit('error', {'message': f'Save error: {str(e)}'})
    
        @socketio.on('update_background')
        def handle_update_background(data):
            """Update background with current frame (for manual background update)"""
            try:
                session = validate_and_get_session(request.sid)
                frame_data = validate_and_get_frame(data)
                update_background(frame_data, session)
                
                emit('background_updated', {
                    'success': True,
                    'message': 'Background updated successfully'
                })
                
            except Exception as e:
                logger.error(f"Error updating background: {str(e)}")
                emit('error', {'message': f'Update error: {str(e)}'})


        @socketio.on('end_session')
        def handle_end_session():
            """End the current session and clean up"""
            try:
                session = validate_and_get_session(request.sid)
                del active_sessions[request.sid]
                
                emit('session_ended', {
                    'success': True,
                    'message': 'Session ended successfully'
                })
                
            except Exception as e:
                logger.error(f"Error ending session: {str(e)}")
                emit('error', {'message': f'End session error: {str(e)}'})
