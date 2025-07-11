# main.py

from dotenv import load_dotenv
from src.workflow import SchedulingWorkflow

load_dotenv()

def main():
    print("🗓️ Agentic AI Scheduler Assistant Initialized")
    scheduler = SchedulingWorkflow()
    result = scheduler.run()

    print("\n📜 Final Scheduling History:")
    print("=" * 50)
    for line in result['history']:
        print(line)

if __name__ == "__main__":
    main()
