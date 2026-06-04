# VinDine Concierge Product SPEC

## Product Requirement

When a group representative enters dining needs, VinDine Concierge must:

1. Extract constraints from natural language.
2. Classify hard constraints and soft preferences.
3. Detect missing information, ambiguity, or conflict.
4. Filter the mock/synthetic in-resort restaurant and kiosk dataset.
5. Rank Top 3 options.
6. Explain why each option was selected.
7. Show trade-offs.
8. Identify who in the group may be least satisfied.
9. Provide fallback options when no exact match exists.
10. Let the user reject a suggestion and re-rank from that correction signal.

## Acceptance Criteria

- Parse location, group size, budget per person, cuisine, voucher, dietary needs, elderly/kids, stroller, quiet preference, and distance limit.
- Do not recommend a restaurant that violates hard dietary, voucher, distance, or accessibility constraints.
- Ask clarification when important information is missing instead of guessing.
- Return structured fallback options when no perfect match exists.
- Each Top 3 card includes score, matched constraints, missed preferences, trade-off, explanation, uncertainty, and a placeholder Google Maps search link.
- User rejection is saved to `data/correction_log.jsonl` and used to re-rank.

## Data Policy

The dataset in `data/vin_restaurants.json` is mock/synthetic data for prototype evaluation. It must not be presented as a complete or official Vinpearl directory. Google Maps links are search placeholders created from restaurant name + zone.

## AI Role

AI is augmentation only. It parses, ranks, explains, and suggests recovery paths. The human user remains the final decider, reviewer, rescuer, and trainer.
