"""
Database Models for AI-CCTV System
Al Noor Factory for Solar Panels
Using SQLAlchemy 2.0 Declarative Mapping
"""
import datetime
import json
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class CameraModel(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Camera")
    stream_type: Mapped[str] = mapped_column(String(10), default="01") # 01=Main, 02=Sub
    status: Mapped[str] = mapped_column(String(50), default="INIT") # LIVE, CONNECTING, OFFLINE
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    resolution: Mapped[str] = mapped_column(String(50), default="1280x720")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    zones: Mapped[List["ZoneModel"]] = relationship("ZoneModel", back_populates="camera", cascade="all, delete-orphan")
    incidents: Mapped[List["IncidentModel"]] = relationship("IncidentModel", back_populates="camera", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "channel_number": self.channel_number,
            "name": self.name,
            "stream_type": self.stream_type,
            "status": self.status,
            "fps": round(self.fps, 1),
            "resolution": self.resolution,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.channel_number"), index=True, nullable=False)
    zone_id_str: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(50), default="workstation") # workstation, restricted, general
    polygon_json: Mapped[str] = mapped_column(Text, default="[]") # JSON list of [ [x, y], ... ]
    absence_threshold_sec: Mapped[int] = mapped_column(Integer, default=120)
    phone_threshold_sec: Mapped[int] = mapped_column(Integer, default=5)
    min_occupancy: Mapped[int] = mapped_column(Integer, default=1)
    max_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    camera: Mapped["CameraModel"] = relationship("CameraModel", back_populates="zones")

    def to_dict(self):
        try:
            poly = json.loads(self.polygon_json)
        except Exception:
            poly = []
        return {
            "id": self.zone_id_str,
            "db_id": self.id,
            "camera_id": self.camera_id,
            "name": self.name,
            "type": self.zone_type,
            "polygon": poly,
            "absence_threshold_sec": self.absence_threshold_sec,
            "phone_threshold_sec": self.phone_threshold_sec,
            "min_occupancy": self.min_occupancy,
            "max_occupancy": self.max_occupancy,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True) # e.g. INC-14-171829384
    camera_id: Mapped[int] = mapped_column(Integer, ForeignKey("cameras.channel_number"), index=True, nullable=False)
    zone_id_str: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # absence, phone, restricted, offline
    severity: Mapped[str] = mapped_column(String(20), default="high") # high, medium, low
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_clip_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Human Review State (Human-in-the-Loop)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True) # pending, verified, dismissed
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    camera: Mapped["CameraModel"] = relationship("CameraModel", back_populates="incidents")

    def to_dict(self):
        return {
            "id": self.id,
            "cam_id": self.camera_id,
            "zone_id": self.zone_id_str,
            "event_type": self.event_type,
            "severity": self.severity,
            "title": self.title,
            "details": self.details,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "",
            "timestamp_epoch": self.timestamp.timestamp() if self.timestamp else 0,
            "duration_sec": self.duration_sec,
            "snapshot_path": self.snapshot_path,
            "video_clip_path": self.video_clip_path,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if self.reviewed_at else None,
            "review_notes": self.review_notes
        }


class EmployeeModel(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) # e.g. EMP-101
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="Solar Assembly Line")
    assigned_zone_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    face_embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False) # Raw float32 array bytes
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_code": self.employee_code,
            "full_name": self.full_name,
            "department": self.department,
            "assigned_zone_id": self.assigned_zone_id,
            "photo_path": self.photo_path,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


class AttendanceLogModel(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), index=True, nullable=False)
    camera_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    zone_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    compliance_status: Mapped[str] = mapped_column(String(50), default="authorized") # authorized, wrong_station, restricted_area

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "camera_id": self.camera_id,
            "zone_id": self.zone_id,
            "first_seen": self.first_seen.strftime("%Y-%m-%d %H:%M:%S") if self.first_seen else "",
            "last_seen": self.last_seen.strftime("%Y-%m-%d %H:%M:%S") if self.last_seen else "",
            "compliance_status": self.compliance_status
        }


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(100), default="System") # Ali, Karrar, AI Engine
    action: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "ZONE_CREATED", "INCIDENT_VERIFIED"
    details: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else ""
        }
