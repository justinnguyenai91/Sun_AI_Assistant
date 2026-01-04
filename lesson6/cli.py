import argparse
from ai.prompt_template import SYSTEM_PROMPT
from ai.decision_parser import parse_ai_response

from data_sources.csv_loader import load_csv
from data_sources.postgres_loader import load_table

from engine.executor import execute_csv, execute_postgres
from engine.validators import validate_instruction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--file")
    parser.add_argument("--table")
    parser.add_argument("--question", required=True)
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    # 1. Call LLM (pseudo)
    ai_response = call_llm(SYSTEM_PROMPT, args.question)

    decision = parse_ai_response(ai_response)

    if "error" in decision:
        print(decision)
        return

    if args.dry_run:
        print("AI Decision:")
        print(decision)
        return

    # 2. Load data + validate + execute
