from typing import List
from datetime import datetime

class SchedulingAgent:
    def __init__(self, name, free_slots, preferences=None):
        self.name = name
        self.free_slots = free_slots
        self.preferences = preferences or {}

    def propose_slots(self, slots: List[tuple]) -> List[tuple]:
        ranked = sorted(slots, key=self.rank_slot)
        return ranked

    def rank_slot(self, slot):
        hour = slot[0].hour
        # Example preference: avoid mornings
        if self.preferences.get("avoid_mornings") and hour < 10:
            return 10
        return 0

    def accept_or_reject(self, proposed_slot):
        # Simulate smart acceptance
        if self.preferences.get("avoid_afternoon") and proposed_slot[0].hour >= 13:
            return False
        return True
