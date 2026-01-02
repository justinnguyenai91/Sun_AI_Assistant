import logging
import pandas as pd

logger = logging.getLogger(__name__)

def load_csv(path: str) -> pd.DataFrame:
    logger.info(f"Loading CSV file: {path}")
    try:
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Failed to load CSV: {e}")
        raise

def summarize(df: pd.DataFrame) -> dict:
    logger.info("Summarizing dataset")
    return {
        "rows": len(df),
        "columns": list(df.columns)
    }
