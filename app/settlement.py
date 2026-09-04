from enum import StrEnum

from pydantic import BaseModel


class SettlementStatus(StrEnum):
    PENDING = "PENDING"
    WON = "WON"
    LOST = "LOST"
    VOID = "VOID"
    UNRESOLVED = "UNRESOLVED"


class ProviderResult(BaseModel):
    provider: str
    event_key: str
    final: bool
    payload: dict


class Reconciliation(BaseModel):
    event_key: str
    status: SettlementStatus
    source_agreement: bool
    providers: list[str]
    reason: str


def reconcile_results(results: list[ProviderResult]) -> Reconciliation:
    if not results:
        raise ValueError("at least one provider result is required")
    event_keys = {r.event_key for r in results}
    if len(event_keys) != 1:
        raise ValueError("results must refer to the same normalized event")

    providers = sorted({r.provider for r in results})
    if not all(r.final for r in results):
        return Reconciliation(
            event_key=results[0].event_key,
            status=SettlementStatus.PENDING,
            source_agreement=False,
            providers=providers,
            reason="One or more result sources are not final.",
        )

    canonical_payloads = {str(sorted(r.payload.items())) for r in results}
    agreement = len(canonical_payloads) == 1
    return Reconciliation(
        event_key=results[0].event_key,
        status=SettlementStatus.UNRESOLVED,
        source_agreement=agreement,
        providers=providers,
        reason=(
            "Result sources agree; market-specific bookmaker rules are still required for settlement."
            if agreement
            else "Result sources disagree; manual or official-source resolution is required."
        ),
    )
