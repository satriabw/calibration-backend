from datetime import datetime
from database import db

class Calibration(db.Model):
    __tablename__ = 'calibration'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.Text, nullable=False)
    version_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default='active', nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Calibration {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version_id': self.version_id,
            'file_name': self.file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'status': self.status
        }
    
    def set_inactive(self):
        """Soft delete the calibration"""
        self.status = 'inactive'
        db.session.commit()
    
    @classmethod
    def get_active(cls):
        """Get all non-deleted calibrations"""
        return cls.query.filter(
            cls.status != 'inactive',
            cls.deleted_at.is_(None)
        ).all()
    
    @classmethod
    def get_by_id(cls, calibration_id):
        """Get calibration by ID if not deleted"""
        return cls.query.filter(
            cls.id == calibration_id,
            cls.status != 'inactive',
            cls.deleted_at.is_(None)
        ).first()
    
    @classmethod
    def get_latest_active_version(cls):
        """Get the latest active version associated with this calibration"""
        return Calibration.query.filter(
            Calibration.status != 'inactive',
            Calibration.deleted_at.is_(None)
        ).order_by(Calibration.version_id.desc()).first()
    
    @classmethod
    def get_calibration_by_name(cls, name):
        """Get calibration by name if not deleted"""
        return cls.query.filter(
            cls.name == name,
            cls.deleted_at.is_(None),
        ).order_by(cls.version_id.desc()).all()


    @classmethod
    def create(cls, name, version_id, file_name):
        """Create or update a calibration by name"""
        calibration = cls.get_latest_active_version()

        # soft delete existing calibration
        if calibration:
            calibration.set_inactive()

        calibration = cls(name=name, version_id=version_id, file_name=file_name)
        db.session.add(calibration)
        db.session.commit()
        return calibration
