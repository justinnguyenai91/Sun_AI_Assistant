import argparse
import logging
import logging.config
from data_utils import load_csv, summarize

def main():
    logging.config.fileConfig("logging.conf")
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Lesson 5 - Advanced Python for AI")
    parser.add_argument("--input", required=True, help="Path to CSV file")
    args = parser.parse_args()

    logger.info("Lesson 5 CLI started")

    df = load_csv(args.input)
    summary = summarize(df)

    logger.info(f"Summary result: {summary}")
    print(summary)

if __name__ == "__main__":
    main()
