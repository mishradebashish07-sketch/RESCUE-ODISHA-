import uuid
import datetime
import urllib.parse
from typing import Optional
from fastapi import FastAPI, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# --- DATABASE SETUP (MySQL) ---
MYSQL_USER = "root"
MYSQL_PASSWORD = urllib.parse.quote_plus("Mishra@2009")
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB = "disaster_db"

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC SCHEMAS ---
class SOSRequest(BaseModel):
    reporter_contact: Optional[str] = Field(None, example="+919876543210")
    message: str = Field(..., example="Flooding near market, 4 people stranded on roof")
    latitude: float = Field(..., ge=-90.0, le=90.0, example=21.4680)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=87.0130)
    category: str = Field("flood_rescue", example="flood_rescue")
    severity_score: int = Field(4, ge=1, le=5)

class TriageResponse(BaseModel):
    distress_id: str
    status: str
    assigned_team: Optional[dict]
    nearest_shelter: Optional[dict]

# --- FASTAPI APP ---
app = FastAPI(title="Innovate Odisha - AI Disaster Response API (MySQL)")

@app.get("/")
def health_check():
    return {"status": "online", "message": "Odisha Disaster Management API is running"}

@app.post("/api/v1/sos/triage", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
def handle_sos_report(payload: SOSRequest, db: Session = Depends(get_db)):
    # Spatial Point format: POINT(lon lat)
    sos_wkt = f"POINT({payload.longitude} {payload.latitude})"
    report_id = str(uuid.uuid4())

    # 1. Spatial Query: Closest shelter with available capacity using ST_Distance_Sphere (returns meters)
    shelter_query = text("""
        SELECT id, name, contact_phone, 
               ST_Distance_Sphere(location, ST_PointFromText(:sos_point, 4326)) AS distance_meters
        FROM shelters
        WHERE current_occupancy < total_capacity
        ORDER BY distance_meters ASC
        LIMIT 1;
    """)
    nearest_shelter = db.execute(shelter_query, {"sos_point": sos_wkt}).mappings().first()

    # 2. Spatial Query: Closest available ODRAF / rescue unit
    responder_query = text("""
        SELECT id, team_name, team_type, 
               ST_Distance_Sphere(location, ST_PointFromText(:sos_point, 4326)) AS distance_meters
        FROM responder_units
        WHERE is_available = TRUE
        ORDER BY distance_meters ASC
        LIMIT 1;
    """)
    closest_responder = db.execute(responder_query, {"sos_point": sos_wkt}).mappings().first()

    shelter_id = str(nearest_shelter["id"]) if nearest_shelter else None
    responder_id = str(closest_responder["id"]) if closest_responder else None
    assigned_status = "ASSIGNED" if closest_responder else "QUEUED"

    # 3. Record distress report in database
    insert_sos = text("""
        INSERT INTO distress_reports (
            id, reporter_contact, raw_message, category, 
            severity_score, location, status, assigned_responder_id, nearest_shelter_id, created_at
        ) VALUES (
            :id, :contact, :message, :category, 
            :score, ST_PointFromText(:sos_point, 4326), :status, :responder_id, :shelter_id, NOW()
        );
    """)
    db.execute(insert_sos, {
        "id": report_id,
        "contact": payload.reporter_contact,
        "message": payload.message,
        "category": payload.category,
        "score": payload.severity_score,
        "sos_point": sos_wkt,
        "status": assigned_status,
        "responder_id": responder_id,
        "shelter_id": shelter_id
    })

    # Mark responder unit as busy
    if responder_id:
        db.execute(
            text("UPDATE responder_units SET is_available = FALSE WHERE id = :resp_id;"),
            {"resp_id": responder_id}
        )

    db.commit()

    # Format return JSON
    shelter_info = None
    if nearest_shelter:
        shelter_info = {
            "id": str(nearest_shelter["id"]),
            "name": nearest_shelter["name"],
            "distance_km": round(nearest_shelter["distance_meters"] / 1000.0, 2),
            "contact": nearest_shelter["contact_phone"]
        }

    team_info = None
    if closest_responder:
        team_info = {
            "id": str(closest_responder["id"]),
            "team_name": closest_responder["team_name"],
            "team_type": closest_responder["team_type"],
            "distance_km": round(closest_responder["distance_meters"] / 1000.0, 2)
        }

    return {
        "distress_id": report_id,
        "status": assigned_status,
        "assigned_team": team_info,
        "nearest_shelter": shelter_info
    }

@app.post("/api/v1/responders/reset")
def reset_responders(db: Session = Depends(get_db)):
    """Resets all responder units back to available status for testing/demos."""
    db.execute(text("UPDATE responder_units SET is_available = TRUE;"))
    db.commit()
    return {"status": "success", "message": "All rescue units are now marked available."}