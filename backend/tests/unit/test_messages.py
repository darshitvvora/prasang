from app.workflows.lead_notification import LeadContext, lead_message


def _ctx(**kw):
    base = dict(lead_id="l1", artist_name="Arjun", artist_email=None, artist_phone="9820011001", artist_whatsapp=None,
                whatsapp_enabled=False, is_locked=False, planner_name="Neha", planner_phone="9920012345", event_title="Wedding",
                event_date="2026-12-12", budget_label="₹15K–25K", notes="150 guests")
    return LeadContext(**(base | kw))


def test_unlocked_lead_message_includes_planner_contact():
    text = lead_message(_ctx())
    assert "Neha" in text and "9920012345" in text and "Wedding" in text and "12 Dec 2026" in text


def test_locked_lead_message_hides_planner_contact():
    text = lead_message(_ctx(is_locked=True))
    assert "9920012345" not in text and "Neha" not in text and "upgrade" in text.lower()
