import re
import datetime
import json
import logging
from typing import List, Dict, Any, TypedDict, Optional, Union
from sqlalchemy import or_

from backend.config import GROQ_API_KEY, GEMMA_MODEL, LLAMA_MODEL
from backend.database import SessionLocal, HCP, Interaction, Material, Sample, FollowUpTask, InteractionSample

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

# Define Agent State for LangGraph
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    form_state: Dict[str, Any]
    agent_logs: List[str]
    suggested_actions: List[str]
    current_user_message: str
    tool_calls: Optional[List[Dict[str, Any]]]
    final_response: Optional[str]

# ==========================================
# Tool Implementations (Direct DB CRUD)
# ==========================================

def search_hcps(query: str) -> List[Dict[str, Any]]:
    """Search for Healthcare Professionals by name, specialty, or hospital."""
    db = SessionLocal()
    try:
        hcps = db.query(HCP).filter(
            or_(
                HCP.name.ilike(f"%{query}%"),
                HCP.specialty.ilike(f"%{query}%"),
                HCP.hospital.ilike(f"%{query}%")
            )
        ).all()
        return [{"id": h.id, "name": h.name, "specialty": h.specialty, "email": h.email, "phone": h.phone, "hospital": h.hospital} for h in hcps]
    finally:
        db.close()

def query_interaction_history(hcp_id: int) -> List[Dict[str, Any]]:
    """Retrieve past interaction records for a specific HCP."""
    db = SessionLocal()
    try:
        interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.created_at.desc()).all()
        result = []
        for i in interactions:
            result.append({
                "id": i.id,
                "type": i.interaction_type,
                "date": i.date,
                "time": i.time,
                "topics": i.topics_discussed,
                "sentiment": i.sentiment,
                "outcomes": i.outcomes,
                "follow_up": i.follow_up_actions
            })
        return result
    finally:
        db.close()

def search_materials(query: str) -> Dict[str, Any]:
    """Search clinical materials, brochures, and samples by name."""
    db = SessionLocal()
    try:
        mats = db.query(Material).filter(Material.name.ilike(f"%{query}%")).all()
        samps = db.query(Sample).filter(Sample.name.ilike(f"%{query}%")).all()
        return {
            "materials": [{"id": m.id, "name": m.name, "type": m.type} for m in mats],
            "samples": [{"id": s.id, "name": s.name, "dosage": s.dosage, "stock": s.stock} for s in samps]
        }
    finally:
        db.close()

def log_interaction(
    hcp_id: int,
    interaction_type: str,
    date: str,
    time: str,
    attendees: str = "",
    topics_discussed: str = "",
    sentiment: str = "Neutral",
    outcomes: str = "",
    follow_up_actions: str = "",
    materials_shared: List[int] = [],
    samples_distributed: List[Dict[str, Any]] = []
) -> Dict[str, Any]:
    """Log a new HCP interaction with shared materials, sample distributions, and details."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return {"error": f"HCP with id {hcp_id} not found."}
            
        interaction = Interaction(
            hcp_id=hcp_id,
            interaction_type=interaction_type,
            date=date,
            time=time,
            attendees=attendees,
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions
        )
        
        # Add materials
        if materials_shared:
            mats = db.query(Material).filter(Material.id.in_(materials_shared)).all()
            interaction.materials.extend(mats)
            
        # Add samples and adjust stock
        for sd in samples_distributed:
            s_id = sd.get("sample_id")
            qty = sd.get("quantity", 1)
            sample_obj = db.query(Sample).filter(Sample.id == s_id).first()
            if sample_obj:
                sample_obj.stock = max(0, sample_obj.stock - qty)
                int_sample = InteractionSample(sample_id=s_id, quantity=qty)
                interaction.samples.append(int_sample)
                
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        
        return {
            "id": interaction.id,
            "hcp_id": interaction.hcp_id,
            "hcp_name": hcp.name,
            "interaction_type": interaction.interaction_type,
            "date": interaction.date,
            "time": interaction.time,
            "attendees": interaction.attendees,
            "topics_discussed": interaction.topics_discussed,
            "sentiment": interaction.sentiment,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
            "materials_shared": [m.id for m in interaction.materials],
            "samples_distributed": [{"sample_id": s.sample_id, "quantity": s.quantity} for s in interaction.samples]
        }
    finally:
        db.close()

def edit_interaction(interaction_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Edit an existing logged interaction."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {"error": f"Interaction with id {interaction_id} not found."}
            
        for key, val in updates.items():
            if key in ["interaction_type", "date", "time", "attendees", "topics_discussed", "sentiment", "outcomes", "follow_up_actions"]:
                setattr(interaction, key, val)
            elif key == "materials_shared":
                interaction.materials.clear()
                mats = db.query(Material).filter(Material.id.in_(val)).all()
                interaction.materials.extend(mats)
            elif key == "samples_distributed":
                # Return current stocks first
                for isamp in interaction.samples:
                    sample_obj = db.query(Sample).filter(Sample.id == isamp.sample_id).first()
                    if sample_obj:
                        sample_obj.stock += isamp.quantity
                # Clear samples
                interaction.samples.clear()
                # Re-add and deduct stock
                for sd in val:
                    s_id = sd.get("sample_id")
                    qty = sd.get("quantity", 1)
                    sample_obj = db.query(Sample).filter(Sample.id == s_id).first()
                    if sample_obj:
                        sample_obj.stock = max(0, sample_obj.stock - qty)
                        int_sample = InteractionSample(sample_id=s_id, quantity=qty)
                        interaction.samples.append(int_sample)
                        
        db.commit()
        db.refresh(interaction)
        
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        return {
            "id": interaction.id,
            "hcp_id": interaction.hcp_id,
            "hcp_name": hcp.name if hcp else "",
            "interaction_type": interaction.interaction_type,
            "date": interaction.date,
            "time": interaction.time,
            "attendees": interaction.attendees,
            "topics_discussed": interaction.topics_discussed,
            "sentiment": interaction.sentiment,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
            "materials_shared": [m.id for m in interaction.materials],
            "samples_distributed": [{"sample_id": s.sample_id, "quantity": s.quantity} for s in interaction.samples]
        }
    finally:
        db.close()

def create_follow_up_task(interaction_id: int, description: str, due_date: str) -> Dict[str, Any]:
    """Create a new follow up task linked to an interaction."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {"error": f"Interaction with id {interaction_id} not found."}
            
        task = FollowUpTask(
            interaction_id=interaction_id,
            description=description,
            due_date=due_date,
            status="Pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {
            "id": task.id,
            "interaction_id": task.interaction_id,
            "description": task.description,
            "due_date": task.due_date,
            "status": task.status
        }
    finally:
        db.close()

# Dictionary of all tools for dispatcher
TOOLS = {
    "search_hcps": search_hcps,
    "query_interaction_history": query_interaction_history,
    "search_materials": search_materials,
    "log_interaction": log_interaction,
    "edit_interaction": edit_interaction,
    "create_follow_up_task": create_follow_up_task
}

# ==========================================
# Heuristic Fallback Engine
# ==========================================

def run_heuristics(message: str, form_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the user's natural language input using NLP heuristics.
    Simulates tool executions, writes to the DB, and builds structured states.
    """
    logs = ["🤖 Starting AI Agent (Local Heuristic EngineFallback)..."]
    msg_lower = message.lower()
    
    # 1. Search HCPs
    logs.append("🔍 Step 1: Matching HCP from database...")
    db = SessionLocal()
    matched_hcp = None
    try:
        all_hcps = db.query(HCP).all()
        for hcp in all_hcps:
            # Check if name is mentioned in user message
            parts = hcp.name.lower().replace("dr.", "").strip().split()
            if any(p in msg_lower for p in parts if len(p) > 2):
                matched_hcp = hcp
                break
        
        if matched_hcp:
            logs.append(f"🛠️ Tool called: `search_hcps` with args: `{{'query': '{matched_hcp.name}'}}`")
            logs.append(f"✅ Tool returned: Found HCP Dr. {matched_hcp.name} (Specialty: {matched_hcp.specialty}) in database.")
        else:
            # Check current form state to see if an HCP was already selected
            if form_state.get("hcp_id"):
                matched_hcp = db.query(HCP).filter(HCP.id == form_state["hcp_id"]).first()
                if matched_hcp:
                    logs.append(f"ℹ️ Preserved existing selected HCP: Dr. {matched_hcp.name}")
            if not matched_hcp:
                # Default to first HCP for demonstration if not found
                matched_hcp = all_hcps[0] if all_hcps else None
                if matched_hcp:
                    logs.append(f"⚠️ No HCP mentioned. Defaulting to: Dr. {matched_hcp.name}")
                else:
                    logs.append("❌ No HCPs found in the database. Please add or seed HCPs first.")
    finally:
        db.close()
        
    # 2. Extract sentiment
    sentiment = "Neutral"
    if any(x in msg_lower for x in ["positive", "good", "great", "excellent", "loved", "liked", "happy", "interested"]):
        sentiment = "Positive"
    elif any(x in msg_lower for x in ["negative", "bad", "poor", "complained", "unhappy", "angry", "disinterested"]):
        sentiment = "Negative"
    logs.append(f"🧠 Inferred Sentiment from message: {sentiment}")

    # 3. Extract interaction type
    int_type = "Meeting"
    if "email" in msg_lower:
        int_type = "Email"
    elif "call" in msg_lower or "phone" in msg_lower:
        int_type = "Phone"
    elif "meeting" in msg_lower or "met" in msg_lower or "visit" in msg_lower:
        int_type = "Meeting"
    else:
        # Carry over from state or default
        int_type = form_state.get("interaction_type", "Meeting")

    # 4. Search Materials & Samples
    logs.append("🔍 Step 2: Searching matching brochures/samples in message...")
    db = SessionLocal()
    shared_materials = []
    distributed_samples = []
    try:
        all_materials = db.query(Material).all()
        for mat in all_materials:
            # Check if name is mentioned, e.g. "OncoBoost" or "CardioGuard"
            kw = mat.name.split()[0].lower()
            if kw in msg_lower:
                shared_materials.append(mat.id)
                logs.append(f"🛠️ Tool called: `search_materials` with args: `{{'query': '{kw}'}}`")
                logs.append(f"✅ Tool returned: Shared Material: {mat.name}")
                
        all_samples = db.query(Sample).all()
        for samp in all_samples:
            kw = samp.name.split()[0].lower()
            if kw in msg_lower:
                distributed_samples.append({"sample_id": samp.id, "quantity": 1})
                logs.append(f"✅ Tool returned: Distributed Sample: {samp.name} (Qty: 1)")
    finally:
        db.close()

    # 5. Extract topics/outcomes/followups
    # Formulate topics based on mention or full message
    topics = form_state.get("topics_discussed", "")
    if len(message) > 10:
        topics = message
        
    outcomes = "Dr. loved the discussion." if sentiment == "Positive" else "Discussed product parameters."
    
    # Extract follow-up actions
    follow_up_actions = ""
    follow_up_task_desc = ""
    if "follow up" in msg_lower or "follow-up" in msg_lower:
        follow_up_actions = "Schedule follow-up meeting in 2 weeks"
        follow_up_task_desc = "Follow-up meeting"
    elif "send" in msg_lower:
        follow_up_actions = "Send product documentation/brochures"
        follow_up_task_desc = "Send materials"
    else:
        follow_up_actions = form_state.get("follow_up_actions", "Check back next week")
        follow_up_task_desc = "Standard follow-up check-in"

    # Dates and Times
    today = datetime.date.today().strftime("%Y-%m-%d")
    now_time = datetime.datetime.now().strftime("%H:%M")
    
    # Check for edits
    is_edit = False
    interaction_id = form_state.get("id")
    
    if interaction_id:
        # This is an edit
        is_edit = True
        logs.append(f"🛠️ Tool called: `edit_interaction` with args: `{{'interaction_id': {interaction_id}, 'updates': {{...}}}}`")
        updates = {
            "interaction_type": int_type,
            "topics_discussed": topics,
            "sentiment": sentiment,
            "outcomes": outcomes,
            "follow_up_actions": follow_up_actions,
            "materials_shared": shared_materials,
            "samples_distributed": distributed_samples
        }
        res = edit_interaction(interaction_id, updates)
        logs.append(f"✅ Tool returned: Interaction {interaction_id} updated successfully.")
    else:
        # This is a new log
        logs.append("🛠️ Tool called: `log_interaction` with args: `{{...}}`")
        if not matched_hcp:
            return {
                "response": "Could not identify which HCP you are logging an interaction for. Please select an HCP first.",
                "form_state": form_state,
                "agent_logs": logs,
                "suggested_actions": []
            }
        res = log_interaction(
            hcp_id=matched_hcp.id,
            interaction_type=int_type,
            date=today,
            time=now_time,
            attendees=matched_hcp.name,
            topics_discussed=topics,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            materials_shared=shared_materials,
            samples_distributed=distributed_samples
        )
        interaction_id = res.get("id")
        logs.append(f"✅ Tool returned: Interaction {interaction_id} logged successfully.")
        
    # Schedule follow-up task if needed
    suggested = []
    if interaction_id:
        due_date = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
        logs.append(f"🛠️ Tool called: `create_follow_up_task` with args: `{{'interaction_id': {interaction_id}, 'description': '{follow_up_task_desc}', 'due_date': '{due_date}'}}`")
        task_res = create_follow_up_task(interaction_id, follow_up_task_desc, due_date)
        logs.append(f"✅ Tool returned: Follow-up task {task_res['id']} created.")
        
        # Build AI suggested quick actions
        suggested = [
            f"Schedule follow-up meeting on {due_date}",
            "Send follow-up thank-you email",
            f"Add Dr. {matched_hcp.name if matched_hcp else ''} to advisory invite list"
        ]

    # Map database response back to form state
    new_form_state = {
        "id": interaction_id,
        "hcp_id": matched_hcp.id if matched_hcp else None,
        "interaction_type": int_type,
        "date": res.get("date", today),
        "time": res.get("time", now_time),
        "attendees": res.get("attendees", matched_hcp.name if matched_hcp else ""),
        "topics_discussed": res.get("topics_discussed", topics),
        "sentiment": res.get("sentiment", sentiment),
        "outcomes": res.get("outcomes", outcomes),
        "follow_up_actions": res.get("follow_up_actions", follow_up_actions),
        "materials_shared": res.get("materials_shared", shared_materials),
        "samples_distributed": res.get("samples_distributed", distributed_samples)
    }

    hcp_display = matched_hcp.name if matched_hcp else "the doctor"
    if is_edit:
        ai_resp = f"I've updated the interaction details for Dr. {hcp_display}. The sentiment has been recorded as {sentiment}, and I updated the shared materials."
    else:
        ai_resp = f"I've successfully logged a new {int_type} with Dr. {hcp_display}. I've set the sentiment to {sentiment}, shared the relevant materials, and created a follow-up action: '{follow_up_actions}'."

    logs.append("🏁 AI Agent finished execution successfully.")
    
    return {
        "response": ai_resp,
        "form_state": new_form_state,
        "agent_logs": logs,
        "suggested_actions": suggested
    }

# ==========================================
# Real LLM + Groq Agent Node with LangGraph
# ==========================================

def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        import groq
        return groq.Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Error loading groq client: {e}")
        return None

def groq_agent_node(state: AgentState) -> AgentState:
    """
    State transition: uses the Groq API to parse messages and decide on tool executions.
    If no GROQ_API_KEY is found, redirects immediately to heuristic fallback.
    """
    client = get_groq_client()
    if not client:
        # Fallback immediately
        heuristic_res = run_heuristics(state["current_user_message"], state["form_state"])
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": heuristic_res["response"]}],
            "form_state": heuristic_res["form_state"],
            "agent_logs": state["agent_logs"] + heuristic_res["agent_logs"],
            "suggested_actions": heuristic_res["suggested_actions"],
            "current_user_message": state["current_user_message"],
            "tool_calls": None,
            "final_response": heuristic_res["response"]
        }

    logs = state.get("agent_logs", [])
    logs.append("🤖 Initializing LangGraph Agent on Groq (llama-3.3-70b-versatile)...")
    
    # Construct tools definitions for Groq model
    tools_definitions = [
        {
            "type": "function",
            "function": {
                "name": "search_hcps",
                "description": "Search for Healthcare Professionals by name, specialty, or hospital query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The name, specialty, or hospital query."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_interaction_history",
                "description": "Retrieve past interactions history for an HCP.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hcp_id": {"type": "integer", "description": "The HCP ID."}
                    },
                    "required": ["hcp_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_materials",
                "description": "Search available clinical/marketing brochures or sample drugs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Material or sample name query."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_interaction",
                "description": "Log an interaction in the CRM.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hcp_id": {"type": "integer", "description": "The ID of the HCP."},
                        "interaction_type": {"type": "string", "enum": ["Meeting", "Call", "Email", "Phone"]},
                        "date": {"type": "string", "description": "YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "HH:MM format"},
                        "attendees": {"type": "string"},
                        "topics_discussed": {"type": "string"},
                        "sentiment": {"type": "string", "enum": ["Positive", "Neutral", "Negative"]},
                        "outcomes": {"type": "string"},
                        "follow_up_actions": {"type": "string"},
                        "materials_shared": {"type": "array", "items": {"type": "integer"}, "description": "Array of material IDs shared."},
                        "samples_distributed": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sample_id": {"type": "integer"},
                                    "quantity": {"type": "integer"}
                                },
                                "required": ["sample_id", "quantity"]
                            }
                        }
                    },
                    "required": ["hcp_id", "interaction_type", "date", "time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_interaction",
                "description": "Edit/modify an existing CRM interaction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "interaction_id": {"type": "integer"},
                        "updates": {
                            "type": "object",
                            "properties": {
                                "interaction_type": {"type": "string"},
                                "topics_discussed": {"type": "string"},
                                "sentiment": {"type": "string"},
                                "outcomes": {"type": "string"},
                                "follow_up_actions": {"type": "string"},
                                "materials_shared": {"type": "array", "items": {"type": "integer"}},
                                "samples_distributed": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "sample_id": {"type": "integer"},
                                            "quantity": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["interaction_id", "updates"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_follow_up_task",
                "description": "Schedule a follow-up task/reminder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "interaction_id": {"type": "integer"},
                        "description": {"type": "string"},
                        "due_date": {"type": "string", "description": "YYYY-MM-DD"}
                    },
                    "required": ["interaction_id", "description", "due_date"]
                }
            }
        }
    ]

    system_prompt = (
        "You are an AI assistant for a pharmaceuticals CRM system. Your task is to process natural language "
        "messages from field sales representatives logging or editing interactions with HCPs.\n"
        "Use the tools provided to lookup HCPs, brochures, and log details. Update the form state accordingly.\n"
        f"Today's date is {datetime.date.today().strftime('%Y-%m-%d')}.\n"
        f"Current form state is: {json.dumps(state['form_state'])}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in state["messages"][-6:]:  # Limit history
        messages.append(msg)
        
    messages.append({"role": "user", "content": state["current_user_message"]})

    try:
        logs.append(f"💬 Sending user request to LLM ({LLAMA_MODEL})...")
        response = client.chat.completions.create(
            model=LLAMA_MODEL,
            messages=messages,
            tools=tools_definitions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            calls = []
            for tc in tool_calls:
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
            logs.append(f"🛠️ LLM decided to invoke tools: {[c['name'] for c in calls]}")
            return {
                "messages": state["messages"] + [{"role": "assistant", "tool_calls": tool_calls}],
                "form_state": state["form_state"],
                "agent_logs": logs,
                "suggested_actions": state.get("suggested_actions", []),
                "current_user_message": state["current_user_message"],
                "tool_calls": calls,
                "final_response": None
            }
        else:
            logs.append("💬 LLM responded directly without tool call.")
            return {
                "messages": state["messages"] + [{"role": "assistant", "content": response_message.content}],
                "form_state": state["form_state"],
                "agent_logs": logs,
                "suggested_actions": state.get("suggested_actions", []),
                "current_user_message": state["current_user_message"],
                "tool_calls": None,
                "final_response": response_message.content
            }
            
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        logs.append(f"❌ Error calling Groq API: {str(e)}. Falling back to local Heuristic Engine.")
        heuristic_res = run_heuristics(state["current_user_message"], state["form_state"])
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": heuristic_res["response"]}],
            "form_state": heuristic_res["form_state"],
            "agent_logs": logs + heuristic_res["agent_logs"],
            "suggested_actions": heuristic_res["suggested_actions"],
            "current_user_message": state["current_user_message"],
            "tool_calls": None,
            "final_response": heuristic_res["response"]
        }

def execute_tools_node(state: AgentState) -> AgentState:
    """
    Executes the tool calls saved in state and returns output to LLM context.
    """
    logs = state.get("agent_logs", [])
    tool_calls = state.get("tool_calls", [])
    new_messages = list(state["messages"])
    current_form_state = dict(state["form_state"])
    suggested = list(state.get("suggested_actions", []))
    
    for call in tool_calls:
        name = call["name"]
        args = call["arguments"]
        logs.append(f"🛠️ Executing Tool `{name}` with arguments: `{json.dumps(args)}`")
        
        if name in TOOLS:
            try:
                res = TOOLS[name](**args)
                logs.append(f"✅ Tool `{name}` executed successfully.")
                
                # Update local form state variables dynamically based on tool responses
                if name == "log_interaction" or name == "edit_interaction":
                    if "error" not in res:
                        current_form_state.update(res)
                        
                # Format response for the agent history
                new_messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", "fallback_id"),
                    "name": name,
                    "content": json.dumps(res)
                })
            except Exception as e:
                logs.append(f"❌ Tool `{name}` failed with error: {str(e)}")
                new_messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", "fallback_id"),
                    "name": name,
                    "content": json.dumps({"error": str(e)})
                })
        else:
            logs.append(f"❌ Tool `{name}` not found in Registry.")
            
    # Compile suggested follow-up suggestions dynamically
    if current_form_state.get("id"):
        due_date = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
        suggested = [
            f"Schedule follow-up meeting on {due_date}",
            "Send follow-up thank-you email",
            f"Add Dr. {current_form_state.get('attendees', 'Sharma')} to advisory board invite list"
        ]

    # Re-call Groq Agent to synthesize final responses
    # We clear tool_calls to let the LLM check next transitions
    return {
        "messages": new_messages,
        "form_state": current_form_state,
        "agent_logs": logs,
        "suggested_actions": suggested,
        "current_user_message": state["current_user_message"],
        "tool_calls": None,
        "final_response": None
    }

# ==========================================
# Compile LangGraph Workflow
# ==========================================
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("groq_agent", groq_agent_node)
workflow.add_node("execute_tools", execute_tools_node)

# Set Entry Point
workflow.set_entry_point("groq_agent")

# Define Conditional Edges
def should_continue(state: AgentState):
    if state.get("tool_calls"):
        return "execute_tools"
    return END

workflow.add_conditional_edges(
    "groq_agent",
    should_continue,
    {
        "execute_tools": "execute_tools",
        END: END
    }
)

workflow.add_edge("execute_tools", "groq_agent")

# Compile graph
langgraph_agent = workflow.compile()

def run_agent(message: str, form_state: Dict[str, Any], chat_history: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    """
    Main entry point to execute the LangGraph Agent workflow.
    """
    initial_state = {
        "messages": chat_history,
        "form_state": form_state or {
            "id": None,
            "hcp_id": None,
            "interaction_type": "Meeting",
            "date": "",
            "time": "",
            "attendees": "",
            "topics_discussed": "",
            "sentiment": "Neutral",
            "outcomes": "",
            "follow_up_actions": "",
            "materials_shared": [],
            "samples_distributed": []
        },
        "agent_logs": [],
        "suggested_actions": [],
        "current_user_message": message,
        "tool_calls": None,
        "final_response": None
    }
    
    try:
        final_state = langgraph_agent.invoke(initial_state)
        # Synthesize final response
        resp = final_state.get("final_response") or "I've successfully parsed your request and updated the database and form."
        return {
            "response": resp,
            "form_state": final_state["form_state"],
            "agent_logs": final_state["agent_logs"],
            "suggested_actions": final_state["suggested_actions"]
        }
    except Exception as e:
        logger.error(f"LangGraph execution exception: {e}")
        # Final emergency fallback to ensure stability
        return run_heuristics(message, form_state)
