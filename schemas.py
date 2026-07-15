from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# HCP Schemas
class HCPBase(BaseModel):
    name: str
    specialty: str
    email: EmailStr
    phone: Optional[str] = None
    hospital: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCPResponse(HCPBase):
    id: int

    class Config:
        from_attributes = True

# Material Schemas
class MaterialBase(BaseModel):
    name: str
    type: str

class MaterialResponse(MaterialBase):
    id: int

    class Config:
        from_attributes = True

# Sample Schemas
class SampleBase(BaseModel):
    name: str
    dosage: Optional[str] = None
    stock: int

class SampleResponse(SampleBase):
    id: int

    class Config:
        from_attributes = True

class InteractionSampleInput(BaseModel):
    sample_id: int
    quantity: int = 1

class InteractionSampleResponse(BaseModel):
    sample_id: int
    name: str
    dosage: Optional[str] = None
    quantity: int

    class Config:
        from_attributes = True

# Follow-Up Task Schemas
class FollowUpTaskBase(BaseModel):
    description: str
    due_date: Optional[str] = None
    status: str = "Pending"

class FollowUpTaskResponse(FollowUpTaskBase):
    id: int
    interaction_id: int

    class Config:
        from_attributes = True

# Interaction Schemas
class InteractionFormState(BaseModel):
    id: Optional[int] = None
    hcp_id: Optional[int] = None
    interaction_type: str = "Meeting"
    date: str = ""
    time: str = ""
    attendees: str = ""
    topics_discussed: str = ""
    sentiment: str = "Neutral"
    outcomes: str = ""
    follow_up_actions: str = ""
    materials_shared: List[int] = []  # IDs of materials shared
    samples_distributed: List[InteractionSampleInput] = [] # List of samples

class InteractionCreate(BaseModel):
    hcp_id: int
    interaction_type: str
    date: str
    time: str
    attendees: Optional[str] = ""
    topics_discussed: Optional[str] = ""
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    materials_shared: List[int] = []
    samples_distributed: List[InteractionSampleInput] = []
    follow_up_tasks: List[FollowUpTaskBase] = []

class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    hcp: HCPResponse
    interaction_type: str
    date: str
    time: str
    attendees: Optional[str] = ""
    topics_discussed: Optional[str] = ""
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    materials: List[MaterialResponse] = []
    samples: List[InteractionSampleResponse] = []
    follow_up_tasks: List[FollowUpTaskResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

# Chat API Schemas
class ChatRequest(BaseModel):
    message: str
    form_state: Optional[InteractionFormState] = None

class ChatResponse(BaseModel):
    response: str
    form_state: InteractionFormState
    agent_logs: List[str] = []
    suggested_actions: List[str] = []
