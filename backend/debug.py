import sys
sys.path.insert(0, ".")
from api.chat import run_chat_turn
import json
result = run_chat_turn("Puedes cambiar el S.O de la ecs-test a Ubuntu 24.04, por favor", "test-session-001")
print("=== REPLY ===")
print(result["reply"])
print("\n=== RAW MESSAGES ===")
for msg in result.get("raw_messages", []):
    print(f"  [{msg['type']}] {str(msg['content'])[:200]}")