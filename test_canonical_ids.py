from arbitragebot.normalization.aggregator import canonical_event_id
from datetime import datetime
from arbitragebot.normalization.schemas import Sport

# All Kalshi markets have "Participant 1" and "Participant 2"
id1 = canonical_event_id(Sport.OTHER, ["Participant 1", "Participant 2"], datetime(2026, 1, 19, 1, 20))
id2 = canonical_event_id(Sport.OTHER, ["Participant 1", "Participant 2"], datetime(2026, 1, 19, 1, 20))
id3 = canonical_event_id(Sport.OTHER, ["Participant 1", "Participant 2"], datetime(2026, 1, 19, 1, 25))

print(f"Same teams, same time: {id1 == id2}")
print(f"Same teams, diff time: {id1 == id3}")
print(f"ID1: {id1[:16]}")
print(f"ID3: {id3[:16]}")
