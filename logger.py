"""
Centralised logging with a `loguru` fallback to stdlib logging.
"""

import logging
import os
import sys

os.makedirs("logs", exist_ok=True)

try:
    from loguru import logger

    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level="DEBUG",
    )
    def _add_file_sink(path: str, *, level: str, rotation: str, retention: str, fmt: str, **extra):
        try:
            logger.add(
                path,
                rotation=rotation,
                retention=retention,
                compression="zip",
                format=fmt,
                level=level,
                enqueue=True,
                **extra,
            )
        except PermissionError:
            logger.add(
                path,
                rotation=rotation,
                retention=retention,
                compression="zip",
                format=fmt,
                level=level,
                enqueue=False,
                **extra,
            )

    _add_file_sink(
        "logs/lexai.log",
        rotation="10 MB",
        retention="7 days",
        fmt="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
        level="INFO",
    )
    _add_file_sink(
        "logs/errors.log",
        rotation="5 MB",
        retention="14 days",
        fmt="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}\n{exception}",
        level="ERROR",
        backtrace=True,
        diagnose=True,
    )
except ModuleNotFoundError:  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/lexai.log", encoding="utf-8"),
        ],
    )
    logger = logging.getLogger("lexai")


def log_pipeline_event(case_id: str, stage: str, status: str, detail: str = ""):
    logger.info(f"[PIPELINE] case={case_id} stage={stage} status={status} {detail}")


def log_agent_call(agent_name: str, tokens_used: int = 0):
    logger.debug(f"[AGENT] {agent_name} called | tokens~{tokens_used}")


def log_rag_retrieval(query_len: int, docs_retrieved: int):
    logger.debug(f"[RAG] query_len={query_len} docs_retrieved={docs_retrieved}")
