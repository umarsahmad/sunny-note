# src/workflow.py

from typing import List
from datetime import datetime, timedelta
import pytz
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

from .models import Participant, SchedulerState
from .agents import SchedulingAgent
from .calender_utils import parse_busy_slots, get_working_hours, get_free_slots

# Participants setup
PARTICIPANTS_DATA = [
    Participant(
        name="Alice",
        time_zone="US/Eastern",
        working_hours=["09:00", "17:00"],
        busy_slots=[["2025-07-10T10:00", "2025-07-10T11:00"]],
        preferences={"avoid_mornings": False}
    ),
    Participant(
        name="Bob",
        time_zone="Europe/London",
        working_hours=["09:00", "17:00"],
        busy_slots=[["2025-07-10T14:00", "2025-07-10T15:00"]],
        preferences={"avoid_afternoon": True}
    ),
    Participant(
        name="Charlie",
        time_zone="Asia/Tokyo",
        working_hours=["09:00", "17:00"],
        busy_slots=[["2025-07-10T16:00", "2025-07-10T17:00"]],
        preferences={"avoid_mornings": True}
    )
]

def build_scheduling_agents(day="2025-07-10") -> List[SchedulingAgent]:
    agents = []
    for p in PARTICIPANTS_DATA:
        busy = parse_busy_slots(p.busy_slots, p.time_zone)
        work_start, work_end = get_working_hours(day, p.working_hours, p.time_zone)
        free_slots = get_free_slots(work_start, work_end, busy)
        agents.append(SchedulingAgent(p.name, free_slots, p.preferences))
    return agents
# agents is list of objects

class SchedulingWorkflow:
    def __init__(self):
        self.day = "2025-07-10"
        self.agents = build_scheduling_agents(self.day)

        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=os.environ["GROQ_API_KEY"],
            model_name="llama-3.1-8b-instant"
        )

        self.workflow = self._build_workflow()

    def _build_workflow(self):
        builder = StateGraph(SchedulerState)

        builder.add_node("Initiator", RunnableLambda(self.initiator_node))
        builder.add_node("Responders", RunnableLambda(self.responder_node))
        builder.add_node("Negotiator", RunnableLambda(self.consensus_check_node))
        builder.add_node("LLMRescheduler", RunnableLambda(self.llm_rescheduler_node))
        builder.add_node("Finalizer", RunnableLambda(self.finalizer_node))

        builder.set_entry_point("Initiator")
        builder.add_edge("Initiator", "Responders")
        builder.add_edge("Responders", "Negotiator")
        # builder.add_conditional_edges(
        #             "Negotiator", {
        #                 # "success": RunnableLambda(self.finalizer_node),
        #                 # "conflict": RunnableLambda(self.llm_rescheduler_node)
        #                 "success": 'Finalizer',
        #                 "conflict": 'LLMRescheduler'
        #                 })

        builder.add_conditional_edges(
                    "Negotiator",
                    lambda state: state._branch,
                    {
                        "success": "Finalizer",
                        "conflict": "LLMRescheduler"
                    }
                )

        builder.add_edge("LLMRescheduler", "Responders")
        builder.set_finish_point("Finalizer")

        return builder.compile()

    def initiator_node(self, state: SchedulerState): # the first person who is starting the meeting as host
        initiator_agent = next(a for a in self.agents if a.name == state.initiator)
        if not state.proposed_slot:
            proposed_range = initiator_agent.propose_slots(initiator_agent.free_slots)
            if not proposed_range:
                state.history.append(f"{state.initiator} has no available slots!")
                return state
            chosen = proposed_range[0]
            state.proposed_slot = chosen[0].isoformat()
            state.history.append(f"{state.initiator} proposes {state.proposed_slot}")
        return state

    def responder_node(self, state: SchedulerState):
        state.accepted.clear()
        state.rejected.clear()
        proposed_start = datetime.fromisoformat(state.proposed_slot)
        proposed_end = proposed_start + timedelta(minutes=30)        # assuming all meetings lasts 30 min
        proposed_range = (proposed_start, proposed_end)

        for agent in self.agents:
            if agent.name == state.initiator:
                continue
            is_free = any(
                fs[0] <= proposed_start and fs[1] >= proposed_end
                for fs in agent.free_slots
            )
            accepts = is_free and agent.accept_or_reject(proposed_range)

            if accepts:
                state.accepted.append(agent.name)
                state.history.append(f"{agent.name} accepts {state.proposed_slot}")
            else:
                state.rejected.append(f"{agent.name}")
                state.history.append(f"{agent.name} rejects {state.proposed_slot}")
        return state

    # def consensus_check_node(self, state):
    #     if len(state.rejected) == 0:
    #         state.final_slot = state.proposed_slot
    #         return {"__branch": "success", "final_slot": state.final_slot}
    #     else:
    #         return {"__branch": "conflict"}
    def consensus_check_node(self, state):
        if len(state.rejected) == 0:
            state.final_slot = state.proposed_slot
            state._branch = "success"
        else:
            state._branch = "conflict"
        print(f"[consensus_check_node] Branch decided: {state._branch}")
        return state


    def llm_rescheduler_node(self, state: SchedulerState):
        initiator_agent = next(a for a in self.agents if a.name == state.initiator)
        remaining_slots = [
            slot for slot in initiator_agent.free_slots
            if slot[0].isoformat() > state.proposed_slot
        ]
        if not remaining_slots:
            state.history.append("No more slots to propose.")
            return state

        # Prepare prompt
        slot_options = "\n".join(
            f"- {s[0].isoformat()} to {s[1].isoformat()}" for s in remaining_slots
        )
        prompt = f"""
                You are a polite AI scheduling assistant.
                The following participants rejected the proposed time {state.proposed_slot}: {', '.join(state.rejected)}.
                Here are the next available time slots:
                {slot_options}
                Please pick the most suitable slot and write a polite suggestion.
                """

        # Call Groq
        response = self.llm.invoke([
                    SystemMessage(content="You are a helpful scheduling assistant."),
                    HumanMessage(content=prompt)
                ])
        content = response.content.strip()
        # For simplicity, pick the first remaining slot
        # new_proposal = remaining_slots[0][0].isoformat() # modify here to use llm to pick the suitaible slot instead of just the first one
        new_proposal = None
        for slot in remaining_slots:
            if slot[0].isoformat() in content:
                new_proposal = slot[0].isoformat()
                break

        state.proposed_slot = new_proposal
        state.history.append(content)
        return state

    def finalizer_node(self, state: SchedulerState):
        if not state.final_slot:
            print("⚠️ No final_slot to confirm!")
            return state    

        # Parse the confirmed time as *naive* first
        print(state.final_slot)
        confirmed_start = datetime.fromisoformat(state.final_slot or "2025-07-10T14:00")
        print(confirmed_start)
        confirmed_end = confirmed_start + timedelta(minutes=30)

        for agent in self.agents:
            # Match timezone to agent's slots
            if agent.free_slots:
                tz = agent.free_slots[0][0].tzinfo
                confirmed_start = confirmed_start.replace(tzinfo=tz)
                confirmed_end = confirmed_end.replace(tzinfo=tz)

            updated = [
                slot for slot in agent.free_slots
                if not (slot[0] <= confirmed_start and slot[1] >= confirmed_end)  # updating the free slots availaibility for the agents by blocking the proposed time out of it.
            ]
            agent.free_slots = updated


        # Compose confirmation email
        prompt = f"""
                    You are a polite AI scheduling assistant.
                    The meeting has been confirmed at {state.final_slot}.
                    Participants: {', '.join([state.initiator] + state.participants)}
                    Please compose a polite confirmation email to send to all participants.
                    """
        response = self.llm.invoke([
                    SystemMessage(content="You are a helpful scheduling assistant."),
                    HumanMessage(content=prompt)
                ])
        email = response.content.strip()
        state.history.append("Confirmation Email:\n" + email)
        return state

    def run(self):
        initial_state = SchedulerState(
            initiator="Alice",
            participants=[a.name for a in self.agents if a.name != "Alice"],
            proposed_slot=None,
            accepted=[],
            rejected=[],
            final_slot=None,
            history=[]
        )
        try:
            result = self.workflow.invoke(initial_state)
            return result
        except Exception as e:
            print("🔥 Error during workflow execution:")
            print(e)
            raise



