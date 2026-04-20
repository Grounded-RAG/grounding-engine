"""Run a focused 18-question grounded QA evaluation over a pilot-dataset fixture."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from app.core.llm_client import generate_grounded_draft
from app.pipeline.contracts import EvidenceItem, EvidencePackage
from app.services.generation import generate_answer_from_evidence


@dataclass(frozen=True)
class EvalQuestion:
    number: int
    query: str
    expected_answer: str


def _evidence_item(
    *,
    citation_id: str,
    chunk_id: str,
    chunk_index: int,
    text: str,
) -> EvidenceItem:
    return EvidenceItem(
        citation_id=citation_id,
        chunk_id=chunk_id,
        tenant_id=uuid4(),
        namespace_id=uuid4(),
        document_id=uuid4(),
        chunk_index=chunk_index,
        text=text,
        score=0.9,
        sources=("dense", "sparse"),
    )


def build_pilot_evidence_package() -> EvidencePackage:
    """Return one compact synthetic evidence package for the Norfield pilot scenario."""

    items = [
        _evidence_item(
            citation_id="E001",
            chunk_id="pilot-overview",
            chunk_index=0,
            text=(
                "Pilot Overview\n"
                "In March 2025, the city of Norfield launched an electric van pilot for municipal service operations. "
                "The pilot lasted through July 2025."
            ),
        ),
        _evidence_item(
            citation_id="E002",
            chunk_id="fleet-details",
            chunk_index=1,
            text=(
                "Fleet Details\n"
                "The city purchased 9 electric vans from Heliox Transit for the pilot. "
                "Each van had a 75 kWh battery pack."
            ),
        ),
        _evidence_item(
            citation_id="E003",
            chunk_id="charging-operations",
            chunk_index=2,
            text=(
                "Charging and Operations\n"
                "The city installed 5 dual-port charging stations at the main logistics hub. "
                "The vans were usually charged between 10:00 PM and 4:30 AM."
            ),
        ),
        _evidence_item(
            citation_id="E004",
            chunk_id="departments",
            chunk_index=3,
            text=(
                "Departments Involved\n"
                "Clinical Logistics used 6 vans. "
                "Public Health Outreach used 3 vans."
            ),
        ),
        _evidence_item(
            citation_id="E005",
            chunk_id="distance",
            chunk_index=4,
            text=(
                "Performance Summary\n"
                "During the pilot, the vans traveled a total of 72,500 kilometers."
            ),
        ),
        _evidence_item(
            citation_id="E006",
            chunk_id="april-event",
            chunk_index=5,
            text=(
                "Incident Log\n"
                "In April 2025, one van had a charging connector fault and was repaired within two days under warranty."
            ),
        ),
        _evidence_item(
            citation_id="E007",
            chunk_id="june-event",
            chunk_index=6,
            text=(
                "Incident Log\n"
                "In June 2025, one van was unavailable for four days because of a thermal management sensor failure."
            ),
        ),
        _evidence_item(
            citation_id="E008",
            chunk_id="staff-feedback",
            chunk_index=7,
            text=(
                "Staff Feedback\n"
                "The most common concern from staff was limited charger availability during schedule disruptions."
            ),
        ),
        _evidence_item(
            citation_id="E009",
            chunk_id="committee-recommendation",
            chunk_index=8,
            text=(
                "Committee Recommendation\n"
                "In August 2025, the committee recommended:\n"
                "- purchase 6 additional electric vans\n"
                "- add 3 more charging ports at the main logistics hub\n"
                "- create a driver guide focused on energy-efficient route planning"
            ),
        ),
        _evidence_item(
            citation_id="E010",
            chunk_id="fuel-cost",
            chunk_index=9,
            text=(
                "Costs and Savings\n"
                "Before the pilot, the city spent $14,800 on fuel over the same period."
            ),
        ),
        _evidence_item(
            citation_id="E011",
            chunk_id="electricity-cost",
            chunk_index=10,
            text=(
                "Costs and Savings\n"
                "During the pilot, electricity costs were $5,600."
            ),
        ),
        _evidence_item(
            citation_id="E012",
            chunk_id="maintenance-old",
            chunk_index=11,
            text=(
                "Maintenance Costs\n"
                "Gasoline van maintenance over the period had previously cost $6,400."
            ),
        ),
        _evidence_item(
            citation_id="E013",
            chunk_id="maintenance-new",
            chunk_index=12,
            text=(
                "Maintenance Costs\n"
                "Electric van maintenance during the pilot cost $2,500."
            ),
        ),
        _evidence_item(
            citation_id="E014",
            chunk_id="installation-cost",
            chunk_index=13,
            text=(
                "Charging Installation\n"
                "Charging installation costs were $11,200."
            ),
        ),
    ]

    return EvidencePackage(
        retrieved_chunk_ids=[item.chunk_id for item in items],
        selected_evidence_ids=[item.chunk_id for item in items],
        items=items,
    )


QUESTIONS = [
    EvalQuestion(1, "When did the pilot start and end?", "It started in March 2025 and ended in July 2025."),
    EvalQuestion(2, "How many electric vans were purchased?", "9"),
    EvalQuestion(3, "Which company supplied the vans?", "Heliox Transit"),
    EvalQuestion(4, "What was the battery capacity of each van?", "75 kWh"),
    EvalQuestion(5, "How many charging stations were installed?", "5 dual-port charging stations"),
    EvalQuestion(6, "Which departments participated, and how many vans did each use?", "Clinical Logistics used 6 vans; Public Health Outreach used 3 vans"),
    EvalQuestion(7, "During what hours were the vans usually charged?", "Between 10:00 PM and 4:30 AM"),
    EvalQuestion(8, "How many total kilometers did the vans travel during the pilot?", "72,500 kilometers"),
    EvalQuestion(9, "What happened in April 2025?", "One van had a charging connector fault and was repaired within two days under warranty."),
    EvalQuestion(10, "What happened in June 2025?", "One van was unavailable for four days because of a thermal management sensor failure."),
    EvalQuestion(11, "What was the most common concern from staff?", "Limited charger availability during schedule disruptions"),
    EvalQuestion(12, "What did the committee recommend in August 2025?", "purchase 6 additional electric vans; add 3 more charging ports at the main logistics hub; create a driver guide focused on energy-efficient route planning"),
    EvalQuestion(13, "What was the difference between old fuel cost and new electricity cost?", "$9,200"),
    EvalQuestion(14, "What was the maintenance savings during the pilot?", "$3,900"),
    EvalQuestion(15, "What was the net savings after including installation costs?", "$1,900"),
    EvalQuestion(16, "What color were the vans?", "The document does not say."),
    EvalQuestion(17, "What battery chemistry did the vans use?", "The document does not say."),
    EvalQuestion(18, "Who is the CEO of Heliox Transit?", "The document does not say."),
]


async def _run_provider_path(evidence_package: EvidencePackage) -> list[tuple[EvalQuestion, str, str]]:
    rows: list[tuple[EvalQuestion, str, str]] = []
    for question in QUESTIONS:
        draft = await generate_answer_from_evidence(
            query_text=question.query,
            evidence_package=evidence_package,
        )
        rows.append((question, draft.answer_text, draft.generator_provider))
    return rows


def _run_local_path(evidence_package: EvidencePackage) -> list[tuple[EvalQuestion, str, str]]:
    rows: list[tuple[EvalQuestion, str, str]] = []
    for question in QUESTIONS:
        draft = generate_grounded_draft(
            query_text=question.query,
            evidence_package=evidence_package,
        )
        rows.append((question, draft.answer_text, draft.generator_provider))
    return rows


def main() -> None:
    evidence_package = build_pilot_evidence_package()
    print("Running pilot evaluation against the current grounded answer engine...")
    print()

    try:
        rows = asyncio.run(_run_provider_path(evidence_package))
    except Exception:
        rows = _run_local_path(evidence_package)

    for question, answer, provider in rows:
        print(f"Q{question.number}. {question.query}")
        print(f"Expected: {question.expected_answer}")
        print(f"Answer:   {answer}")
        print(f"Provider: {provider}")
        print()


if __name__ == "__main__":
    main()
