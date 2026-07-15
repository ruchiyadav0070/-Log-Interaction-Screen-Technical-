import sys
import os
import json

# Add parent directory to path so we can run from within backend folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal, HCP, Interaction
from backend.agent import run_agent

def run_tests():
    print("=== Testing Database Initialization ===")
    init_db()
    
    db = SessionLocal()
    try:
        hcps = db.query(HCP).all()
        print(f"Database seeded with {len(hcps)} HCPs:")
        for hcp in hcps:
            print(f"- ID {hcp.id}: {hcp.name} ({hcp.specialty}) - Hospital: {hcp.hospital}")
            
        if len(hcps) == 0:
            print("ERROR: Database seeding failed.")
            return
            
        print("\n=== Testing AI Agent (Heuristic Fallback and LangGraph Structure) ===")
        test_message = "I spoke with Dr. Ramesh Sharma today. We discussed the OncoBoost brochure. The sentiment was positive and he liked the trial parameters. Follow up next week."
        print(f"Input message: '{test_message}'")
        
        # Test agent invocation
        initial_form_state = {
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
        }
        
        result = run_agent(test_message, initial_form_state)
        
        print("\n--- Agent Response ---")
        print(result["response"])
        
        print("\n--- Extracted Form State ---")
        print(json.dumps(result["form_state"], indent=2))
        
        print("\n--- Agent Trace Logs (LangGraph Steps) ---")
        for log in result["agent_logs"]:
            try:
                print(log)
            except UnicodeEncodeError:
                print(log.encode('utf-8', 'ignore').decode('cp1252', 'ignore'))
            
        # Verify database record creation
        logged_id = result["form_state"]["id"]
        if logged_id:
            interaction_record = db.query(Interaction).filter(Interaction.id == logged_id).first()
            if interaction_record:
                print(f"\n[SUCCESS] Found logged interaction in DB with ID: {interaction_record.id}")
                print(f"   HCP ID: {interaction_record.hcp_id}")
                print(f"   Type: {interaction_record.interaction_type}")
                print(f"   Sentiment: {interaction_record.sentiment}")
                print(f"   Topics: {interaction_record.topics_discussed}")
                print(f"   Follow ups: {interaction_record.follow_up_actions}")
            else:
                print("\n[FAILURE] Could not find logged interaction in database.")
        else:
            print("\n[FAILURE] Agent did not return a valid logged interaction ID.")
            
    except Exception as e:
        print(f"Exception encountered during tests: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
