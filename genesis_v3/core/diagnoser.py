from typing import Dict

class Diagnoser:
    def diagnose(self, evidence: Dict) -> Dict:
        # Simple diagnoser for MVP
        if evidence.get('error'):
            return {"failure_type":"EXISTING_BUG","confidence":0.9, "evidence":evidence}
        return {"failure_type":"UNKNOWN","confidence":0.2, "evidence":evidence}
