import logging


def setup_logging(level):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
        handlers=[
            logging.FileHandler("bot/app.log", mode="a"),
            logging.StreamHandler(),
        ]
    )

    logger = logging.getLogger(__name__)
    return logger
