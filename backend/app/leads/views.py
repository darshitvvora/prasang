"""Lead → contract shapes. Locked leads hide the planner's contact details."""
from app.contract import ArtistLead
from app.labels import EVENT_TYPE_LABELS


def to_artist_lead(lead) -> ArtistLead:
    return ArtistLead(
        id=str(lead.id), planner_name=lead.planner_name,
        planner_phone=None if lead.is_locked else lead.planner_phone,
        planner_email=None if lead.is_locked else lead.planner_email,
        event_type=lead.event_type, event_title=EVENT_TYPE_LABELS[lead.event_type], event_date=lead.event_date,
        event_city=lead.event_city, budget_min=lead.budget_min, budget_max=lead.budget_max, notes=lead.notes,
        status=lead.status, is_locked=lead.is_locked, created_at=lead.created_at,
    )
