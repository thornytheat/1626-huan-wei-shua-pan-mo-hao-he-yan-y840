from collections import Counter, defaultdict


def reservations(candidates, remaining, resource_cap):
    issued = set()
    reasons = {}
    usage = Counter()
    taken = defaultdict(set)
    for row in candidates:
        slots = set(range(row.tick, row.tick + row.units))
        lane = (row.resource, row.calendar_day)
        if row.units > remaining:
            reasons[row.case_id] = "QUOTA_REACHED"
        elif usage[row.resource] + row.units > resource_cap:
            reasons[row.case_id] = "RESOURCE_CEILING"
        elif taken[lane] & slots:
            reasons[row.case_id] = "WINDOW_COLLISION"
        else:
            taken[lane].update(slots)
            issued.add(row.case_id)
            usage[row.resource] += row.units
            remaining -= row.units
    return issued, reasons
