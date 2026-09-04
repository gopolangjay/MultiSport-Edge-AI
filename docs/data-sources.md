# Data-source policy

MultiSport Edge AI separates **market discovery**, **sports statistics/results**, and **bookmaker settlement**.

## Bookmaker market layer

Target bookmakers are Betway South Africa and Sportingbet South Africa. Their public sites expose broad sports and market coverage, but this repository does not assume that a public webpage is an unrestricted machine API.

Adapters must use one of:

1. an official/contracted API or feed;
2. a licensed third-party odds feed that explicitly permits the intended use; or
3. a controlled import supplied by the operator.

No undocumented private endpoint is committed as a production dependency until its use is verified as permitted.

## Results/statistics layer

Flashscore and Sofascore are intended as reconciliation/statistics sources where access is permitted. They are not treated as the bookmaker's authoritative settlement engine.

Every result record should preserve provider, provider event id, capture timestamp, raw payload/reference, normalized event id and final/provisional state.

## Settlement layer

A prediction can be marked WON/LOST/VOID only after applying the exact market's bookmaker rules. Cross-source score agreement alone is insufficient for settlement because overtime, abandoned events, player participation, dead heats and sport-specific rules can differ.

## Auditability

Raw provider records should be immutable. Normalization, prediction, portfolio construction, reconciliation and settlement should each write separate audit records so historical decisions can be reproduced.
