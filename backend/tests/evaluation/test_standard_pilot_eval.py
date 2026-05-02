"""Focused evaluation coverage for the 18-question pilot scenario."""

from __future__ import annotations

from scripts.run_standard_pilot_eval import QUESTIONS, build_pilot_evidence_package

from app.core.llm_client import generate_grounded_draft


def test_standard_pilot_eval_questions_regressions() -> None:
    """The pilot scenario should preserve the current strong Standard answers."""

    evidence_package = build_pilot_evidence_package()
    answers = {
        question.number: generate_grounded_draft(
            query_text=question.query,
            evidence_package=evidence_package,
        ).answer_text
        for question in QUESTIONS
    }

    assert "March 2025" in answers[1]
    assert "July 2025" in answers[1]
    assert answers[2] == "9 electric vans [E002]"
    assert answers[3] == "Heliox Transit [E002]"
    assert answers[4] == "75 kWh [E002]"
    assert answers[5] == "5 dual-port charging stations [E003]"
    assert answers[6] == "Clinical Logistics used 6 vans; Public Health Outreach used 3 vans [E004]"
    assert answers[7] == "Between 10:00 PM and 4:30 AM [E003]"
    assert answers[8] == "72,500 kilometers [E005]"
    assert "charging connector fault" in answers[9]
    assert "thermal management sensor failure" in answers[10]
    assert "limited charger availability" in answers[11]
    assert "purchase 6 additional electric vans" in answers[12]
    assert answers[13] == "$9,200 [E010] [E011]"
    assert answers[14] == "$3,900 [E012] [E013]"
    assert answers[15] == "$1,900 [E010] [E011] [E012] [E013] [E014]"
    assert answers[16] == "I could not find the answer in the provided context."
    assert answers[17] == "I could not find the answer in the provided context."
    assert answers[18] == "I could not find the answer in the provided context."
