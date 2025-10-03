from datetime import datetime, time

# Define London and New York Killzones (UTC time)
LONDON_START = time(7, 0)
LONDON_END   = time(10, 0)
NY_START     = time(12, 0)
NY_END       = time(16, 0)

def in_killzone(current_time: datetime) -> bool:
    """Check if given UTC datetime is inside London/NY killzones."""
    t = current_time.time()
    if LONDON_START <= t <= LONDON_END:
        return True
    if NY_START <= t <= NY_END:
        return True
    return False
