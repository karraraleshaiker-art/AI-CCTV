"""
Database Connection & Session Management
AI-CCTV Solar Factory Platform
SQLAlchemy Async Engine with SQLite WAL Mode & Fast Concurrency
"""
import asyncio
import datetime
import json
from pathlib import Path
from typing import AsyncGenerator, List, Optional
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from models import Base, CameraModel, ZoneModel, IncidentModel, AuditLogModel

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "cctv.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 15}
)

# Enable SQLite WAL mode (Write-Ahead Logging) & High-Performance PRAGMAs
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db(settings_data: Optional[dict] = None):
    """Initializes tables and seeds cameras & zones from settings.json if empty."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial configuration if empty
    async with AsyncSessionLocal() as session:
        # Check if cameras exist
        result = await session.execute(select(CameraModel))
        existing_cams = result.scalars().all()
        
        if not existing_cams and settings_data:
            print("[DATABASE] Seeding initial cameras and zones into SQLite database...")
            active_cams = settings_data.get("active_cameras", [14, 15])
            default_stream = settings_data.get("default_stream", "01")
            
            for cam_id in active_cams:
                cam = CameraModel(
                    channel_number=cam_id,
                    name=f"Assembly Line Cam D{cam_id}",
                    stream_type=default_stream,
                    status="CONNECTING",
                    is_active=True
                )
                session.add(cam)
                await session.flush()

                # Seed zones for this camera
                cam_zones = settings_data.get("zones", {}).get(str(cam_id), [])
                for z in cam_zones:
                    zone = ZoneModel(
                        camera_id=cam_id,
                        zone_id_str=z.get("id", f"z_{cam_id}"),
                        name=z.get("name", "Workstation"),
                        zone_type=z.get("type", "workstation"),
                        polygon_json=json.dumps(z.get("polygon", [])),
                        absence_threshold_sec=settings_data.get("absence_threshold_sec", 120),
                        phone_threshold_sec=settings_data.get("phone_duration_sec", 5),
                        min_occupancy=z.get("min_occupancy", 1),
                        max_occupancy=z.get("max_occupancy", 0)
                    )
                    session.add(zone)

            # Add initial Audit Log
            log = AuditLogModel(
                actor="System Setup",
                action="INITIALIZE_DATABASE",
                details="SQLite WAL Database initialized with initial cameras and zones."
            )
            session.add(log)
            await session.commit()
            print("[DATABASE] Initial database seeding completed.")

# ---------------------------------------------------------------------------
# Database Service Helper Functions (CRUD)
# ---------------------------------------------------------------------------
async def db_save_incident(incident_dict: dict):
    """Persists an incident into the database."""
    async with AsyncSessionLocal() as session:
        # Check if incident already exists
        result = await session.execute(select(IncidentModel).where(IncidentModel.id == incident_dict["id"]))
        existing = result.scalar_one_or_none()
        if existing:
            return existing.to_dict()

        # Ensure camera exists to prevent FK violation
        cam_result = await session.execute(select(CameraModel).where(CameraModel.channel_number == incident_dict["cam_id"]))
        cam = cam_result.scalar_one_or_none()
        if not cam:
            cam = CameraModel(channel_number=incident_dict["cam_id"], name=f"Camera D{incident_dict['cam_id']}")
            session.add(cam)
            await session.flush()

        inc = IncidentModel(
            id=incident_dict["id"],
            camera_id=incident_dict["cam_id"],
            zone_id_str=incident_dict.get("zone_id"),
            event_type=incident_dict["event_type"],
            severity=incident_dict.get("severity", "high"),
            title=incident_dict["title"],
            details=incident_dict.get("details", ""),
            timestamp=datetime.datetime.utcnow(),
            duration_sec=incident_dict.get("duration_sec", 0),
            status="pending"
        )
        session.add(inc)
        await session.commit()
        return inc.to_dict()

async def db_get_incidents(limit: int = 50) -> List[dict]:
    """Fetches recent incidents ordered by timestamp descending."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(IncidentModel).order_by(IncidentModel.timestamp.desc()).limit(limit)
        )
        incidents = result.scalars().all()
        return [i.to_dict() for i in incidents]

async def db_update_incident_review(incident_id: str, action: str, reviewer: str = "Supervisor", notes: str = ""):
    """Updates the human review decision (verified / dismissed) for an incident."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(IncidentModel).where(IncidentModel.id == incident_id))
        inc = result.scalar_one_or_none()
        if inc:
            inc.status = action
            inc.reviewed_by = reviewer
            inc.reviewed_at = datetime.datetime.utcnow()
            inc.review_notes = notes
            
            # Log action
            audit = AuditLogModel(
                actor=reviewer,
                action=f"INCIDENT_{action.upper()}",
                details=f"Incident {incident_id} marked as {action}."
            )
            session.add(audit)
            await session.commit()
            return inc.to_dict()
        return None

async def db_get_zones_for_cam(cam_id: int) -> List[dict]:
    """Retrieves all zones defined for a specific camera."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ZoneModel).where(ZoneModel.camera_id == cam_id))
        zones = result.scalars().all()
        return [z.to_dict() for z in zones]

async def db_save_zones_for_cam(cam_id: int, zones_list: list):
    """Replaces or saves zones for a camera."""
    async with AsyncSessionLocal() as session:
        # Delete existing zones for this camera
        result = await session.execute(select(ZoneModel).where(ZoneModel.camera_id == cam_id))
        existing = result.scalars().all()
        for ez in existing:
            await session.delete(ez)
        
        # Insert updated zones
        for z in zones_list:
            zn = ZoneModel(
                camera_id=cam_id,
                zone_id_str=z.get("id", f"z_{cam_id}_{int(datetime.datetime.utcnow().timestamp())}"),
                name=z.get("name", "Zone"),
                zone_type=z.get("type", "workstation"),
                polygon_json=json.dumps(z.get("polygon", [])),
                absence_threshold_sec=z.get("absence_threshold_sec", 120),
                phone_threshold_sec=z.get("phone_threshold_sec", 5),
                min_occupancy=z.get("min_occupancy", 1),
                max_occupancy=z.get("max_occupancy", 0)
            )
            session.add(zn)

        audit = AuditLogModel(
            actor="User",
            action="ZONES_UPDATED",
            details=f"Updated {len(zones_list)} zones on Camera D{cam_id}."
        )
        session.add(audit)
        await session.commit()

# ---------------------------------------------------------------------------
# Employee Biometric & Attendance Management (CRUD)
# ---------------------------------------------------------------------------
async def db_get_employees() -> List[dict]:
    """Fetches all registered employees."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EmployeeModel).order_by(EmployeeModel.id.asc()))
        emps = result.scalars().all()
        return [e.to_dict() for e in emps]

async def db_save_employee(
    full_name: str,
    employee_code: str,
    department: str,
    assigned_zone_id: Optional[str],
    face_embedding: bytes,
    photo_path: Optional[str] = None
) -> dict:
    """Enrolls or updates an employee with biometric embedding."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EmployeeModel).where(EmployeeModel.employee_code == employee_code))
        emp = result.scalar_one_or_none()
        if emp:
            emp.full_name = full_name
            emp.department = department
            emp.assigned_zone_id = assigned_zone_id
            emp.face_embedding = face_embedding
            if photo_path:
                emp.photo_path = photo_path
        else:
            emp = EmployeeModel(
                employee_code=employee_code,
                full_name=full_name,
                department=department,
                assigned_zone_id=assigned_zone_id,
                face_embedding=face_embedding,
                photo_path=photo_path,
                is_active=True
            )
            session.add(emp)

        audit = AuditLogModel(
            actor="Admin",
            action="EMPLOYEE_ENROLLED",
            details=f"Employee {full_name} ({employee_code}) enrolled with biometric facial embedding."
        )
        session.add(audit)
        await session.commit()
        return emp.to_dict()

async def db_delete_employee(emp_id: int) -> bool:
    """Deletes an employee profile."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EmployeeModel).where(EmployeeModel.id == emp_id))
        emp = result.scalar_one_or_none()
        if emp:
            code = emp.employee_code
            name = emp.full_name
            await session.delete(emp)
            audit = AuditLogModel(
                actor="Admin",
                action="EMPLOYEE_DELETED",
                details=f"Employee {name} ({code}) deleted."
            )
            session.add(audit)
            await session.commit()
            return True
        return False

async def db_load_all_face_embeddings():
    """Loads all active employee face embeddings as numpy arrays into memory."""
    import numpy as np
    roster = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EmployeeModel).where(EmployeeModel.is_active == True))
        emps = result.scalars().all()
        for e in emps:
            if e.face_embedding:
                try:
                    arr = np.frombuffer(e.face_embedding, dtype=np.float32)
                    roster.append((e.id, e.full_name, e.employee_code, e.assigned_zone_id, arr))
                except Exception as err:
                    print(f"[DB] Error unpacking embedding for {e.full_name}: {err}")
    return roster

