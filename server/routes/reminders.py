"""Reminders and nudges rule definitions.

Provides:
- GET /v1/reminders/rules: rule templates evaluated locally on device.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reminders", tags=["reminders"])

REMINDER_RULES = [
    {
        "id": "period_upcoming_3d",
        "category": "cycle_phase",
        "condition": "days_before_expected <= 3",
        "message_key": "reminder.period_upcoming.v1",
        "title": "Period Expected Soon",
        "text": "Your period may start in approximately 3 days. Having supplies ready can help you feel prepared.",
        "icon": "calendar",
        "action": "view_calendar"
    },
    {
        "id": "follicular_energy_boost",
        "category": "lifestyle",
        "condition": "phase == 'follicular'",
        "message_key": "nudge.follicular_energy.v1",
        "title": "Energy Renewal",
        "text": "Estrogen levels rise during the follicular phase, often bringing refreshed physical energy and mental clarity.",
        "icon": "sun",
        "action": "read_card",
        "card_id": 1
    },
    {
        "id": "iron_rich_food_nudge",
        "category": "nutrition",
        "condition": "phase == 'menstrual'",
        "message_key": "nudge.iron_food.v1",
        "title": "Nutrient Support",
        "text": "Iron-rich foods like leafy greens, lentils, ragi, and jaggery help nourish your body during menstrual flow.",
        "icon": "droplet",
        "action": "read_card",
        "card_id": 4
    },
    {
        "id": "hydration_reminder",
        "category": "lifestyle",
        "condition": "always",
        "message_key": "nudge.hydration.v1",
        "title": "Stay Hydrated",
        "text": "Drinking sufficient clean water daily helps reduce bloating, supports circulation, and eases fatigue.",
        "icon": "droplet",
        "action": "dismiss"
    },
    {
        "id": "log_prompt_reminder",
        "category": "logging",
        "condition": "days_since_last_cycle >= 28",
        "message_key": "reminder.log_prompt.v1",
        "title": "Cycle Log Check-In",
        "text": "A quick log of how you are feeling helps keep your personal baseline accurate.",
        "icon": "edit",
        "action": "open_log"
    }
]


@router.get("/rules")
def get_reminder_rules():
    """Returns rule definitions for on-device reminder scheduling and nudges."""
    return {
        "version": "1.0.0",
        "evaluation": "on_device",
        "rules": REMINDER_RULES,
        "privacy_note": "Rule conditions are evaluated strictly on your phone without sending dates or symptoms."
    }
