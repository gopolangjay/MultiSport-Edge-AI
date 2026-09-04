from openai import OpenAI

from app.config import get_settings
from app.domain import Candidate


def explain_candidate(candidate: Candidate, evidence: dict) -> str | None:
    """Explain a numerical prediction; never create or alter its probability/confidence."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model="gpt-5",
        input=(
            "Explain this sports-model candidate in concise analytical language. "
            "Do not change, invent, or reinterpret its probability or confidence. "
            "Flag missing/contextual evidence and correlation risk.\n"
            f"Candidate: {candidate.model_dump_json()}\nEvidence: {evidence}"
        ),
    )
    return response.output_text
