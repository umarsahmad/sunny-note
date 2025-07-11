# main.py

from src.workflow import SchedulingWorkflow

def main():
    print("📅 Agentic AI Scheduling Assistant")

    workflow = SchedulingWorkflow()

    while True:
        cmd = input("\n▶️ Type 'schedule' to propose a meeting, or 'quit' to exit: ").strip().lower()

        if cmd in {"quit", "exit"}:
            print("👋 Bye!")
            break

        if cmd == "schedule":
            result = workflow.run()
            print("\n✅ Scheduling Transcript")
            print("=" * 60)
            for line in result.history:
                print(line)
        else:
            print("❓ Unknown command. Type 'schedule' or 'quit'.")

if __name__ == "__main__":
    main()
