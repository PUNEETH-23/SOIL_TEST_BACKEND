# ============================================================
#  CORRECTED Soil Backend - Aligned with Actual DB Schema
# ============================================================

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, conlist
from typing import Optional, List
from datetime import datetime
import uuid

# Rule-based recommendation engine
from recommendation_engine import generate_recommendation

# =========================
# CONFIG
# =========================
DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/agri_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="teamkrushisoilkit")

# =========================
# DB MODELS  ← fixed to match actual CSV schema
# =========================

class Admin(Base):
    """
    Table: admin
    Columns: id (integer PK), email (varchar), password (varchar)
    NOTE: 'admin' table uses integer PK — different from 'admins' table.
    """
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, autoincrement=True)  # FIX: was String, DB has integer
    email = Column(String, unique=True)
    password = Column(String)


class AdminUser(Base):
    """
    Table: admins
    Columns: id (varchar PK), username (varchar), password (varchar)
    NOTE: This table was completely MISSING from original code.
    'admins' uses varchar PK and has 'username' (not 'email').
    """
    __tablename__ = "admins"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)   # FIX: was 'email' in admin; this table has 'username'
    password = Column(String)


class Farmer(Base):
    """
    Table: farmers
    Columns: id (varchar), name (varchar), email (varchar)
    """
    __tablename__ = "farmers"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)


class Land(Base):
    """
    Table: lands
    Columns: id, farmer_id (FK), location, current_crop (nullable), planted_date (nullable)
    """
    __tablename__ = "lands"
    id = Column(String, primary_key=True)
    farmer_id = Column(String, ForeignKey("farmers.id"))
    location = Column(String)
    current_crop = Column(String, nullable=True)
    planted_date = Column(DateTime, nullable=True)


class Test(Base):
    """
    Table: tests
    Columns: id, land_id (FK), avg_ph/n/p/k/moisture/ec (float), created_at
    """
    __tablename__ = "tests"
    id = Column(String, primary_key=True)
    land_id = Column(String, ForeignKey("lands.id"))
    avg_ph = Column(Float)
    avg_n = Column(Float)
    avg_p = Column(Float)
    avg_k = Column(Float)
    avg_moisture = Column(Float)
    avg_ec = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Sample(Base):
    """
    Table: samples
    Columns: id, test_id (FK), ph/n/p/k/moisture/ec (float)
    """
    __tablename__ = "samples"
    id = Column(String, primary_key=True)
    test_id = Column(String, ForeignKey("tests.id"))
    ph = Column(Float)
    n = Column(Float)
    p = Column(Float)
    k = Column(Float)
    moisture = Column(Float)
    ec = Column(Float)


class Recommendation(Base):
    """
    Table: recommendations
    Columns: id (varchar PK), test_id (FK), result (varchar)
    NOTE: This table was completely MISSING from original code.
    """
    __tablename__ = "recommendations"
    id = Column(String, primary_key=True)
    test_id = Column(String, ForeignKey("tests.id"))
    result = Column(String)   # stores the AI/rule-engine recommendation text


# =========================
# Pydantic SCHEMAS
# =========================

class AdminLogin(BaseModel):
    email: str
    password: str


class AdminUserLogin(BaseModel):
    """Login schema for 'admins' table (username-based)."""
    username: str
    password: str


class SampleIn(BaseModel):
    ph: float = Field(..., ge=0, le=14)
    n: float = Field(..., ge=0)
    p: float = Field(..., ge=0)
    k: float = Field(..., ge=0)
    moisture: float = Field(..., ge=0, le=100)
    ec: float = Field(..., ge=0)


class IngestData(BaseModel):
    farmer_id: str
    land_id: str
    current_crop: Optional[str] = None
    planted_date: Optional[datetime] = None
    samples: conlist(SampleIn, min_length=5, max_length=5)


# =========================
# DB DEPENDENCY
# =========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTH HELPERS
# =========================

def require_admin(request: Request):
    if not request.session.get("admin_id"):
        raise HTTPException(status_code=401, detail="Admin login required")


# =========================
# UTIL
# =========================

def avg(values):
    return sum(values) / len(values)





# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"msg": "Soil Backend running"}


# =========================
# ADMIN AUTH (admin table — integer PK, email login)
# =========================

@app.post("/admin/login")
def admin_login(data: AdminLogin, request: Request, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == data.email).first()
    if not admin or admin.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["admin_id"] = str(admin.id)
    return {"msg": "Login successful"}


@app.post("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return {"msg": "Logged out"}


# =========================
# ADMINS AUTH (admins table — varchar PK, username login)
# FIX: This entire section was missing from original code
# =========================

@app.post("/admins/login")
def admins_login(data: AdminUserLogin, request: Request, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if not admin or admin.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["admin_id"] = admin.id
    return {"msg": "Login successful (admins)"}


# =========================
# ADMIN: LIST FARMERS
# =========================

@app.get("/admin/farmers")
def list_farmers(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    farmers = db.query(Farmer).all()
    result = []
    for f in farmers:
        land_count = db.query(Land).filter(Land.farmer_id == f.id).count()
        result.append({"id": f.id, "name": f.name, "email": f.email, "land_count": land_count})
    return result


# =========================
# ADMIN: LIST LANDS
# =========================

@app.get("/admin/lands")
def list_lands(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    lands = db.query(Land).all()
    return [{"id": l.id, "farmer_id": l.farmer_id, "location": l.location,
             "current_crop": l.current_crop, "planted_date": l.planted_date} for l in lands]


# =========================
# ADMIN: ADD FARMER
# =========================

@app.post("/admin/farmer")
def add_farmer(
    farmer_id: str,
    name: str,
    email: str,
    request: Request,
    db: Session = Depends(get_db)
):
    require_admin(request)
    if db.query(Farmer).filter(Farmer.id == farmer_id).first():
        raise HTTPException(status_code=400, detail="Farmer ID already exists")
    farmer = Farmer(id=farmer_id, name=name, email=email)
    db.add(farmer)
    db.commit()
    return {"msg": "Farmer added"}


# =========================
# ADMIN: ADD LAND
# =========================

@app.post("/admin/land")
def add_land(
    land_id: str,
    farmer_id: str,
    location: str,
    request: Request,
    db: Session = Depends(get_db)
):
    require_admin(request)
    if not db.query(Farmer).filter(Farmer.id == farmer_id).first():
        raise HTTPException(status_code=404, detail="Farmer not found")
    land = Land(id=land_id, farmer_id=farmer_id, location=location)
    db.add(land)
    db.commit()
    return {"msg": "Land added"}


# =========================
# ESP32 INGEST
# =========================

@app.post("/ingest")
def ingest(data: IngestData, db: Session = Depends(get_db)):

    # Ensure farmer exists
    farmer = db.query(Farmer).filter(Farmer.id == data.farmer_id).first()
    if not farmer:
        farmer = Farmer(id=data.farmer_id, name="Unknown", email="")
        db.add(farmer)

    # Ensure land exists
    land = db.query(Land).filter(Land.id == data.land_id).first()
    if not land:
        land = Land(id=data.land_id, farmer_id=data.farmer_id, location="Unknown")

    if data.current_crop:
        land.current_crop = data.current_crop

    # FIX: also store planted_date if provided (column exists in DB, was missing in original)
    if data.planted_date:
        land.planted_date = data.planted_date

    db.add(land)
    db.commit()

    # Compute averages
    ph       = avg([s.ph       for s in data.samples])
    n        = avg([s.n        for s in data.samples])
    p        = avg([s.p        for s in data.samples])
    k        = avg([s.k        for s in data.samples])
    moisture = avg([s.moisture for s in data.samples])
    ec       = avg([s.ec       for s in data.samples])

    test_id = str(uuid.uuid4())

    test = Test(
        id=test_id,
        land_id=data.land_id,
        avg_ph=ph,
        avg_n=n,
        avg_p=p,
        avg_k=k,
        avg_moisture=moisture,
        avg_ec=ec
    )
    db.add(test)
    db.commit()

    # Store individual samples
    for i, s in enumerate(data.samples):
        db.add(Sample(
            id=f"{test_id}_{i}",
            test_id=test_id,
            ph=s.ph, n=s.n, p=s.p, k=s.k,
            moisture=s.moisture, ec=s.ec
        ))

    # Generate recommendation via Rule Engine -> HuggingFace LLM
    recommendation_text = generate_recommendation(
        avg_ph=ph, avg_n=n, avg_p=p, avg_k=k,
        avg_moisture=moisture, avg_ec=ec,
        current_crop=data.current_crop
    )

    rec = Recommendation(
        id=str(uuid.uuid4()),
        test_id=test_id,
        result=recommendation_text
    )
    db.add(rec)
    db.commit()

    return {
        "status": "success",
        "test_id": test_id,
        "recommendation": recommendation_text
    }


# =========================
# GET RECOMMENDATION BY TEST
# FIX: This endpoint was missing — 'recommendations' table was never exposed
# =========================

@app.get("/recommendations/{test_id}")
def get_recommendation(test_id: str, db: Session = Depends(get_db)):
    rec = db.query(Recommendation).filter(Recommendation.test_id == test_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="No recommendation found for this test")
    return {
        "test_id": test_id,
        "result": rec.result
    }


# =========================
# FARMER VIEW (read-only, no login required)
# =========================

@app.get("/farmer/{farmer_id}")
def get_farmer_data(farmer_id: str, db: Session = Depends(get_db)):
    lands = db.query(Land).filter(Land.farmer_id == farmer_id).all()

    result = []
    for land in lands:
        tests = db.query(Test).filter(Test.land_id == land.id).all()

        tests_out = []
        for t in tests:
            # FIX: include recommendation result alongside each test
            rec = db.query(Recommendation).filter(Recommendation.test_id == t.id).first()
            tests_out.append({
                "test_id": t.id,
                "ph": t.avg_ph,
                "n": t.avg_n,
                "p": t.avg_p,
                "k": t.avg_k,
                "moisture": t.avg_moisture,
                "ec": t.avg_ec,
                "date": t.created_at,
                "recommendation": rec.result if rec else None
            })

        result.append({
            "land_id": land.id,
            "location": land.location,
            "current_crop": land.current_crop,
            "planted_date": land.planted_date,
            "tests": tests_out
        })

    return result


# =========================
# ADMIN: VIEW ALL TESTS (with recommendations)
# =========================

@app.get("/admin/tests")
def get_all_tests(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    tests = db.query(Test).order_by(Test.created_at.desc()).all()
    out = []
    for t in tests:
        rec = db.query(Recommendation).filter(Recommendation.test_id == t.id).first()
        out.append({
            "test_id": t.id,
            "land_id": t.land_id,
            "avg_ph": t.avg_ph,
            "avg_n": t.avg_n,
            "avg_p": t.avg_p,
            "avg_k": t.avg_k,
            "avg_moisture": t.avg_moisture,
            "avg_ec": t.avg_ec,
            "created_at": t.created_at,
            "recommendation": rec.result if rec else None
        })
    return out


# =========================
# STARTUP
# =========================

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Seed default admin (admin table — integer PK, email-based)
    admin = db.query(Admin).filter(Admin.email == "admin@example.com").first()
    if not admin:
        db.add(Admin(email="admin@example.com", password="admin123"))
        db.commit()

    # Seed default admins entry (admins table — varchar PK, username-based)
    admin_user = db.query(AdminUser).filter(AdminUser.username == "superadmin").first()
    if not admin_user:
        db.add(AdminUser(id=str(uuid.uuid4()), username="superadmin", password="admin123"))
        db.commit()

    db.close()
