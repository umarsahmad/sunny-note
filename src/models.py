from pydantic import BaseModel
from typing import List, Optional

class Participant(BaseModel):
    """
    The format of the all participants or agents data.
    """
    name: str
    time_zone: str
    working_hours: List[str]  # ["09:00", "17:00"]
    busy_slots: List[List[str]]  # [["2025-07-10T10:00", "2025-07-10T11:00"]]
    preferences: Optional[dict] = {}

class SchedulerState(BaseModel):
    initiator: str
    participants: List[str]
    proposed_slot: Optional[str]
    accepted: List[str] = []
    rejected: List[str] = []
    final_slot: Optional[str]
    history: List[str] = []
