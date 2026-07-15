from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from backend.config import PORT, HOST
from backend.database import get_db, init_db, HCP, Interaction, Material, Sample, FollowUpTask, InteractionSample, interaction_material
from backend.schemas import (
    HCPResponse, MaterialResponse, SampleResponse,
    InteractionCreate, InteractionResponse, InteractionFormState,
    ChatRequest, ChatResponse
)
from backend.agent import run_agent, log_interaction, edit_interaction

app = FastAPI(title="AI-First CRM HCP Module API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run database schema creation and seeding on startup
@app.on_event("startup")
def startup_event():
    print("Database initializing...")
    init_db()

# --- Health check ---
@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# --- HCP Endpoints ---
@app.get("/api/hcps", response_model=List[HCPResponse])
def get_hcps(db: Session = Depends(get_db)):
    return db.query(HCP).all()

# --- Material Endpoints ---
@app.get("/api/materials", response_model=List[MaterialResponse])
def get_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()

# --- Sample Endpoints ---
@app.get("/api/samples", response_model=List[SampleResponse])
def get_samples(db: Session = Depends(get_db)):
    return db.query(Sample).all()

# --- Interaction Endpoints ---
@app.get("/api/interactions", response_model=List[InteractionResponse])
def get_interactions(db: Session = Depends(get_db)):
    # Retrieve all interactions sorted by created_at desc
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()

@app.post("/api/interactions", response_model=InteractionResponse)
def create_interaction_api(payload: InteractionCreate, db: Session = Depends(get_db)):
    # Convert samples input schema to matching format for log_interaction function
    samples_in = [{"sample_id": s.sample_id, "quantity": s.quantity} for s in payload.samples_distributed]
    
    res = log_interaction(
        hcp_id=payload.hcp_id,
        interaction_type=payload.interaction_type,
        date=payload.date,
        time=payload.time,
        attendees=payload.attendees or "",
        topics_discussed=payload.topics_discussed or "",
        sentiment=payload.sentiment or "Neutral",
        outcomes=payload.outcomes or "",
        follow_up_actions=payload.follow_up_actions or "",
        materials_shared=payload.materials_shared,
        samples_distributed=samples_in
    )
    
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
        
    # Schedule follow-up tasks if defined in payload
    interaction_id = res["id"]
    for task in payload.follow_up_tasks:
        follow_up_task = FollowUpTask(
            interaction_id=interaction_id,
            description=task.description,
            due_date=task.due_date,
            status=task.status
        )
        db.add(follow_up_task)
    db.commit()
    
    # Retrieve complete interaction record
    interaction_record = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    return interaction_record

@app.put("/api/interactions/{interaction_id}", response_model=InteractionResponse)
def update_interaction_api(interaction_id: int, payload: InteractionFormState, db: Session = Depends(get_db)):
    samples_in = [{"sample_id": s.sample_id, "quantity": s.quantity} for s in payload.samples_distributed]
    
    updates = {
        "interaction_type": payload.interaction_type,
        "date": payload.date,
        "time": payload.time,
        "attendees": payload.attendees,
        "topics_discussed": payload.topics_discussed,
        "sentiment": payload.sentiment,
        "outcomes": payload.outcomes,
        "follow_up_actions": payload.follow_up_actions,
        "materials_shared": payload.materials_shared,
        "samples_distributed": samples_in
    }
    
    res = edit_interaction(interaction_id, updates)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
        
    interaction_record = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    return interaction_record

# --- Chat AI Endpoint ---
@app.post("/api/chat", response_model=ChatResponse)
def chat_ai(payload: ChatRequest):
    # Prepare form state dict from pydantic schema
    form_dict = {}
    if payload.form_state:
        form_dict = payload.form_state.dict()
    
    # Execute agent workflow
    agent_output = run_agent(
        message=payload.message,
        form_state=form_dict,
        chat_history=[]  # Can extend this to maintain context sessions
    )
    
    # Cast form_state back to schemas Pydantic structure
    fs = agent_output["form_state"]
    form_state_response = InteractionFormState(
        id=fs.get("id"),
        hcp_id=fs.get("hcp_id"),
        interaction_type=fs.get("interaction_type", "Meeting"),
        date=fs.get("date", ""),
        time=fs.get("time", ""),
        attendees=fs.get("attendees", ""),
        topics_discussed=fs.get("topics_discussed", ""),
        sentiment=fs.get("sentiment", "Neutral"),
        outcomes=fs.get("outcomes", ""),
        follow_up_actions=fs.get("follow_up_actions", ""),
        materials_shared=fs.get("materials_shared", []),
        samples_distributed=[{"sample_id": s["sample_id"], "quantity": s["quantity"]} for s in fs.get("samples_distributed", [])]
    )
    
    return ChatResponse(
        response=agent_output["response"],
        form_state=form_state_response,
        agent_logs=agent_output["agent_logs"],
        suggested_actions=agent_output["suggested_actions"]
    )

# --- Simulated Voice-to-Text Transcription ---
@app.post("/api/voice-summarize")
def voice_summarize(payload: ChatRequest):
    # Simulated voice transcription text depending on selected HCP or state
    transcripts = [
        "Met Dr. Ramesh Sharma at City Cancer Center today around 11am. We had a great discussion regarding the OncoBoost clinical trial. He requested the Phase 3 brochure and is highly interested. Follow up in two weeks.",
        "Talked to Dr. Priya Patel on the phone. Discussed CardioGuard efficacy rates. Her sentiment was neutral. She wants to see full patient data. Schedule check-in for next week.",
        "Quick meeting with Dr. John Smith regarding NeuroShield. He had some concerns about side effects, so sentiment was somewhat negative. He asked for the dosage guidelines brochure. I will send them today."
    ]
    
    import random
    selected_transcript = random.choice(transcripts)
    
    # Process transcript through the agent
    agent_output = run_agent(
        message=selected_transcript,
        form_state=payload.form_state.dict() if payload.form_state else {}
    )
    
    fs = agent_output["form_state"]
    form_state_response = InteractionFormState(
        id=fs.get("id"),
        hcp_id=fs.get("hcp_id"),
        interaction_type=fs.get("interaction_type", "Meeting"),
        date=fs.get("date", ""),
        time=fs.get("time", ""),
        attendees=fs.get("attendees", ""),
        topics_discussed=fs.get("topics_discussed", ""),
        sentiment=fs.get("sentiment", "Neutral"),
        outcomes=fs.get("outcomes", ""),
        follow_up_actions=fs.get("follow_up_actions", ""),
        materials_shared=fs.get("materials_shared", []),
        samples_distributed=[{"sample_id": s["sample_id"], "quantity": s["quantity"]} for s in fs.get("samples_distributed", [])]
    )
    
    return {
        "transcript": selected_transcript,
        "chat_response": ChatResponse(
            response=agent_output["response"],
            form_state=form_state_response,
            agent_logs=agent_output["agent_logs"],
            suggested_actions=agent_output["suggested_actions"]
        )
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
