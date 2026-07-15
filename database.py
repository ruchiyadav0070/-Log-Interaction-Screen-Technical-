from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import DATABASE_URL

Base = declarative_base()

# Many-to-many relationship association table for Interaction and Material
interaction_material = Table(
    'interaction_material',
    Base.metadata,
    Column('interaction_id', Integer, ForeignKey('interactions.id', ondelete='CASCADE'), primary_key=True),
    Column('material_id', Integer, ForeignKey('materials.id', ondelete='CASCADE'), primary_key=True)
)

class HCP(Base):
    __tablename__ = 'hcps'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    hospital = Column(String(200), nullable=True)

    interactions = relationship("Interaction", back_populates="hcp")

class Interaction(Base):
    __tablename__ = 'interactions'

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey('hcps.id', ondelete='CASCADE'), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # Meeting, Email, Phone, Call, etc.
    date = Column(String(20), nullable=False)  # YYYY-MM-DD
    time = Column(String(20), nullable=False)  # HH:MM
    attendees = Column(String(255), nullable=True)  # Comma separated
    topics_discussed = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    materials = relationship("Material", secondary=interaction_material, back_populates="interactions")
    samples = relationship("InteractionSample", back_populates="interaction", cascade="all, delete-orphan")
    follow_up_tasks = relationship("FollowUpTask", back_populates="interaction", cascade="all, delete-orphan")

class Material(Base):
    __tablename__ = 'materials'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)  # Clinical Study, Brochure, Slide Deck, etc.

    interactions = relationship("Interaction", secondary=interaction_material, back_populates="materials")

class InteractionSample(Base):
    __tablename__ = 'interaction_samples'

    interaction_id = Column(Integer, ForeignKey('interactions.id', ondelete='CASCADE'), primary_key=True)
    sample_id = Column(Integer, ForeignKey('samples.id', ondelete='CASCADE'), primary_key=True)
    quantity = Column(Integer, default=1)

    interaction = relationship("Interaction", back_populates="samples")
    sample = relationship("Sample", back_populates="interactions")

class Sample(Base):
    __tablename__ = 'samples'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dosage = Column(String(50), nullable=True)
    stock = Column(Integer, default=0)

    interactions = relationship("InteractionSample", back_populates="sample")

class FollowUpTask(Base):
    __tablename__ = 'follow_up_tasks'

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey('interactions.id', ondelete='CASCADE'), nullable=False)
    description = Column(String(255), nullable=False)
    due_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    status = Column(String(20), default="Pending")  # Pending, Completed

    interaction = relationship("Interaction", back_populates="follow_up_tasks")

# Database Setup Helper
# Connect args check is required for SQLite specific configurations
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    # Check if database is already seeded
    if db.query(HCP).first() is None:
        print("Seeding database...")
        # Seed HCPs
        hcps = [
            HCP(name="Dr. Ramesh Sharma", specialty="Oncology", email="dr.sharma@oncocare.com", phone="+91 98765 43210", hospital="City Cancer Center"),
            HCP(name="Dr. Priya Patel", specialty="Cardiology", email="dr.patel@heartcare.com", phone="+91 98765 43211", hospital="Metro Heart Institute"),
            HCP(name="Dr. John Smith", specialty="Neurology", email="jsmith@neuroclinic.org", phone="+1 555-0199", hospital="Brain and Spine Clinic"),
            HCP(name="Dr. Anita Desai", specialty="Pediatrics", email="anita.desai@pediatrics.org", phone="+91 98765 43212", hospital="Children's Wellness Hospital")
        ]
        db.add_all(hcps)

        # Seed Materials
        materials = [
            Material(name="OncoBoost Phase III Clinical Trial Brochure", type="Clinical Study Brochure"),
            Material(name="CardioGuard Product Efficacy Sheet", type="Product Sheet"),
            Material(name="NeuroShield Dosage Guidelines", type="Dosage Guide"),
            Material(name="PediatraCare Multi-Nutritional Guide", type="Brochure")
        ]
        db.add_all(materials)

        # Seed Samples
        samples = [
            Sample(name="OncoBoost 10mg Starter Kit", dosage="10mg", stock=100),
            Sample(name="CardioGuard 20mg Samples", dosage="20mg", stock=250),
            Sample(name="NeuroShield 50mg Tablets", dosage="50mg", stock=150),
            Sample(name="PediatraCare Liquid Supplement", dosage="100ml", stock=80)
        ]
        db.add_all(samples)
        
        db.commit()
        print("Seeding completed successfully.")
    db.close()
