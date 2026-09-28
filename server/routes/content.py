"""Content endpoints for education cards and screening message copy.

Provides:
- GET /v1/content/cards?lang=en|hi|mr&topic=pcos|anemia|thyroid|myths|general
- GET /v1/content/messages?lang=en|hi|mr
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/content", tags=["content"])
CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"

# Static fallback cards when content files are not present
DEFAULT_CARDS = [
    {
        "id": 1,
        "topic": "general",
        "title": "What is a Normal Cycle",
        "body": "Menstrual cycles typically range between 21 and 35 days, though every body has its own natural rhythm. Variations of a few days from month to month are common and usually normal. Tracking your cycle length and flow over several months helps establish what is typical for you. If your cycle consistently falls outside this range or stops completely, consider consulting a doctor for personal guidance.",
        "icon": "calendar",
        "audio_ref": "content/audio/en/card_1.mp3",
        "sources": ["WHO-2023-CYCLE", "ACOG-FAQ049"]
    },
    {
        "id": 2,
        "topic": "myths",
        "title": "Irregular Periods and Hormones",
        "body": "It is a common belief that irregular periods are solely caused by daily stress. While temporary stress can shift ovulation by a few days, persistent changes in cycle timing or missed periods often involve hormonal regulation. Nutrition, thyroid hormone balance, and ovary signaling all play important roles. When cycle irregularity continues across multiple months, consider consulting a doctor to explore the underlying causes.",
        "icon": "info",
        "audio_ref": "content/audio/en/card_2.mp3",
        "sources": ["NHS-IRREGULAR", "ICMR-PCOS-GUIDELINES"]
    },
    {
        "id": 3,
        "topic": "pcos",
        "title": "Understanding PCOS Patterns",
        "body": "Polycystic ovary syndrome, or PCOS, is a common hormonal condition affecting roughly one in ten women of reproductive age. Common signs include longer or missed cycles, persistent acne, and hair thinning. It is a manageable condition that responds well to lifestyle adjustments, balanced nutrition, and medical support. Tracking changes helps you spot patterns early. If you notice these patterns, consider consulting a doctor for testing.",
        "icon": "activity",
        "audio_ref": "content/audio/en/card_3.mp3",
        "sources": ["WHO-PCOS-FACTSHEET", "ROTTERDAM-2004"]
    },
    {
        "id": 4,
        "topic": "anemia",
        "title": "Heavy Flow and Iron Levels",
        "body": "Bleeding heavily during periods, such as needing to change protection every two hours, can gradually deplete your iron reserves. This may lead to symptoms like feeling unusually tired, breathless on stairs, or experiencing dizziness. Iron-rich foods like leafy spinach, lentils, ragi, and jaggery support your body during recovery. If your flow remains consistently heavy or fatigue persists, consider consulting a doctor for a simple blood check.",
        "icon": "droplet",
        "audio_ref": "content/audio/en/card_4.mp3",
        "sources": ["WHO-ANEMIA-CUTOFFS", "FIGO-AUB-2018"]
    },
    {
        "id": 5,
        "topic": "thyroid",
        "title": "Thyroid Health and Your Cycle",
        "body": "The thyroid gland in your neck regulates how quickly your body uses energy. When thyroid hormone levels are lower or higher than usual, menstrual cycles can become noticeably longer, shorter, or irregular, alongside changes in body weight or energy. A routine blood test can verify thyroid function easily. If you notice persistent cycle shifts together with fatigue or unexplained weight changes, consider consulting a doctor.",
        "icon": "heart",
        "audio_ref": "content/audio/en/card_5.mp3",
        "sources": ["ATA-THYROID-GUIDELINES"]
    },
    {
        "id": 7,
        "topic": "myths",
        "title": "Facts About Period Taboos",
        "body": "Many cultural myths suggest that menstrual blood is impure or that women must avoid kitchens, worship, and physical activity. In truth, menstrual blood is a natural tissue shedding from the uterine lining, identical in cleanliness to any other bodily process. Resting when uncomfortable is wise, but restrictions are cultural rather than biological. If severe symptoms restrict your daily life, consider consulting a doctor.",
        "icon": "smile",
        "audio_ref": "content/audio/en/card_7.mp3",
        "sources": ["UNICEF-MENSTRUAL-HEALTH"]
    }
]

# Static fallback message skeleton conforming to detector output and CLAUDE.md rule 1
DEFAULT_MESSAGES = {
    "flag.none.v1": {
        "title": "Cycle Pattern Within Personal Baseline",
        "summary": "Your recent cycle fits your historical rhythm.",
        "meaning": "No significant drift was observed in your cycle length, flow, or symptom patterns compared to your baseline.",
        "next_steps": "Continue regular self-tracking. If you ever feel unwell or have health concerns, consider consulting a doctor.",
        "doctor_consult": "If you experience unusual symptoms or discomfort, consider consulting a doctor.",
        "myth_card_id": 1
    },
    "flag.irregularity.v1": {
        "title": "Cycle Length Variation Observed",
        "summary": "Your cycle length shifted notably from your normal baseline.",
        "meaning": "Your cycle was longer or shorter than your historical range. Occasional shifts happen due to travel, stress, or temporary lifestyle factors.",
        "next_steps": "Observe your next cycle. If irregular patterns continue across multiple months, consider consulting a doctor.",
        "doctor_consult": "For recurring irregular cycles, consider consulting a doctor.",
        "myth_card_id": 2
    },
    "flag.pcos_pattern.v1": {
        "title": "PCOS-Like Screening Pattern Noticed",
        "summary": "Longer cycles paired with symptom changes match a pattern sometimes seen in PCOS.",
        "meaning": "This screening flag reflects cycle lengthening alongside acne or hair pattern changes. This is a risk screening indicator, not a clinical determination.",
        "next_steps": "Keep a steady record of your symptoms and cycle timing. Share your self-tracking summary with a healthcare professional.",
        "doctor_consult": "To evaluate these hormonal patterns accurately, consider consulting a doctor.",
        "myth_card_id": 3
    },
    "flag.anemia_pattern.v1": {
        "title": "Anemia-Like Screening Pattern Noticed",
        "summary": "Heavy bleeding accompanied by fatigue matches an anemia-related pattern.",
        "meaning": "Higher menstrual flow together with reports of dizziness or unusual tiredness suggests a potential risk of low iron.",
        "next_steps": "Prioritize iron-rich foods and adequate hydration. Record your daily flow and tiredness levels carefully.",
        "doctor_consult": "For persistent heavy bleeding or fatigue, consider consulting a doctor for a routine blood count.",
        "myth_card_id": 4
    },
    "flag.thyroid_pattern.v1": {
        "title": "Thyroid-Like Screening Pattern Noticed",
        "summary": "Cycle timing shifts alongside fatigue or weight changes match a thyroid pattern.",
        "meaning": "A noticeable shift in cycle length paired with systemic signs like fatigue or mood shifts can be linked to metabolic regulation.",
        "next_steps": "Track any changes in cold sensitivity, energy, and sleep. A healthcare provider can check thyroid levels with a simple blood test.",
        "doctor_consult": "To review these metabolic and cycle signals, consider consulting a doctor.",
        "myth_card_id": 5
    },
    "confidence.low": "Low confidence: based on limited cycle history.",
    "confidence.medium": "Medium confidence: consistent signal across recent cycles.",
    "confidence.high": "High confidence: multiple corroborating signals persisted over multiple cycles.",
    "signals": {
        "cycle_length_high": "Cycle length noticeably longer than your baseline",
        "cycle_length_low": "Cycle length noticeably shorter than your baseline",
        "flow_high": "Menstrual flow noticeably heavier than usual",
        "pain_high": "Period discomfort higher than your personal typical level",
        "acne_high": "Skin breakout changes noted",
        "excess_hair_high": "Excess body hair changes noted",
        "hair_loss_high": "Hair thinning changes noted",
        "fatigue_high": "Fatigue levels elevated above usual",
        "dizziness_high": "Feelings of dizziness reported",
        "pallor_high": "Paleness noted",
        "weight_change_high": "Notable weight shift observed",
        "mood_high": "Mood shifts noted"
    }
}


@router.get("/cards")
def get_cards(
    lang: Literal["en", "hi", "mr"] = Query("en", description="Content language"),
    topic: Optional[Literal["pcos", "anemia", "thyroid", "myths", "general"]] = Query(
        None, description="Optional topic filter"
    ),
):
    """Returns education cards for the requested language and optional topic."""
    cards_path = CONTENT_DIR / lang / "cards.json"
    if cards_path.is_file():
        try:
            cards = json.loads(cards_path.read_text(encoding="utf-8"))
        except Exception:
            cards = DEFAULT_CARDS
    else:
        cards = DEFAULT_CARDS

    if topic:
        cards = [c for c in cards if c.get("topic") == topic]
    return {"lang": lang, "topic": topic, "count": len(cards), "cards": cards}


@router.get("/messages")
def get_messages(
    lang: Literal["en", "hi", "mr"] = Query("en", description="Message dictionary language")
):
    """Returns screening message copy and signal descriptions."""
    msg_path = CONTENT_DIR / lang / "messages.json"
    if msg_path.is_file():
        try:
            data = json.loads(msg_path.read_text(encoding="utf-8"))
            return {"lang": lang, "messages": data}
        except Exception:
            return {"lang": lang, "messages": DEFAULT_MESSAGES}
    return {"lang": lang, "messages": DEFAULT_MESSAGES}
