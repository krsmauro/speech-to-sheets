from speech_to_sheets.pipeline.catch_up import catch_up
from tests.pipeline_world import ALLOWED, World

DAY = 24 * 60 * 60
HOUR = 60 * 60


def look(world: World, now: float) -> int:
    """One catch-up round at `now`, with 30 days of dedupe retention."""
    return catch_up(world.dm, world.services, ALLOWED, 30, now)
