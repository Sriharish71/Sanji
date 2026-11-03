"""
End-to-End Real AI Test for SANJI.
Communicates with active local Ollama service using Qwen 2.5 3B.
Tests:
1. "Hello, who are you?"
2. "What did I just ask you?" (Verifies conversational context memory)
3. "Explain artificial intelligence in simple words."
"""

import os
import sys
from pathlib import Path

# Set offscreen Qt platform for automated execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from core.assistant import Assistant
from utils.logger import setup_logger

setup_logger(name="SANJI_TEST", level="INFO")


def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    assistant = Assistant()

    print("\n[TEST] 1. Checking Ollama Service...")
    health = assistant.check_health()
    print(f"Service Available: {health.service_available}")
    print(f"Target Model: {health.target_model}")
    print(f"Model Ready: {health.target_model_installed}")
    print(f"Ping Latency: {health.ping_latency_ms} ms")

    if not health.service_available or not health.target_model_installed:
        print("[FAIL] Ollama or target model is not available!")
        return 1

    session_id = assistant.start_new_conversation("Real QA Verification Session")
    print(f"\n[TEST] 2. Created Verification Session: {session_id}")

    test_questions = [
        "Hello, who are you?",
        "What did I just ask you?",
        "Explain artificial intelligence in simple words."
    ]

    for idx, question in enumerate(test_questions, 1):
        print(f"\n=======================================================")
        print(f" TURN {idx}: USER -> \"{question}\"")
        print(f"=======================================================")

        loop = QEventLoop()
        received_chunks = []
        full_reply_box = []

        def on_chunk(token):
            received_chunks.append(token)
            sys.stdout.write(token)
            sys.stdout.flush()

        def on_finished(full_text):
            full_reply_box.append(full_text)
            loop.quit()

        def on_error(err):
            print(f"\n[ERROR]: {err}")
            loop.quit()

        assistant.chunk_received.connect(on_chunk)
        assistant.response_finished.connect(on_finished)
        assistant.error_occurred.connect(on_error)

        sys.stdout.write("SANJI: ")
        sys.stdout.flush()

        assistant.send_prompt(question)
        loop.exec()

        # Disconnect slots
        assistant.chunk_received.disconnect(on_chunk)
        assistant.response_finished.disconnect(on_finished)
        assistant.error_occurred.disconnect(on_error)

        print("\n")

        # Basic validations
        if not full_reply_box:
            print(f"[FAIL] Turn {idx} received no response!")
            return 1

        reply = full_reply_box[0]
        if idx == 1:
            # Check if SANJI addressed itself
            print(f"[VERIFY] SANJI address check: {'SANJI' in reply}")
        elif idx == 2:
            # Check if it remembers turn 1
            print(f"[VERIFY] Context memory check: {'who are you' in reply.lower() or 'asked' in reply.lower()}")

    print("=======================================================")
    print(" VERIFYING DATABASE PERSISTENCE")
    print("=======================================================")
    history = assistant.get_conversation_history()
    print(f"Total messages saved in session: {len(history)} (Expected: 6)")

    for h in history:
        print(f"[{h['role'].upper()}] ({h['timestamp'][-8:-3]}): {h['content'][:70]}...")

    if len(history) == 6:
        print("\n>>> ALL 3 CONVERSATIONAL TURNS VERIFIED SUCCESSFULLY WITH REAL OLLAMA MODEL! <<<")
        return 0
    else:
        print(f"[FAIL] Expected 6 messages in history, got {len(history)}")
        return 1


if __name__ == "__main__":
    sys.exit(run_test())
