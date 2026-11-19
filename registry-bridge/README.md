# registry-bridge

Design a public service with XStack, then build it on Registry Stack.

XStack stops at a tested prototype and a build spec. It does not write the back end: identity, payments, the register, the back-office queue. This plugin takes one chosen XStack design and hands it to Registry Stack, without calling XStack's mock platform API and without translating the design by hand.

It lives in this fork of XStack, in its own folder. XStack is by Public Digital and is MIT licensed. So is this plugin.

**Early work.** Today the plugin has the hand-off contract and its first skill. Later skills will need Registry Stack repositories that are not public yet.

## What's here

| Path | What it is |
|---|---|
| `references/handoff.md` | The hand-off contract, field by field |
| `references/handoff.schema.json` | The contract as JSON Schema |
| `references/required-from.json` | The 13 things Registry Stack needs that XStack does not ask, and what each level (alpha, beta, live) requires |
| `scripts/validate_handoff.py` | Validates a `service-handoff.yaml` |
| `skills/design-to-handoff/` | Turns one XStack prototype iteration into a `service-handoff.yaml`, with evals |
| `pilots/household-support-grant/` | The hand-off for the Kestria Household Support Grant example, written by hand |
| `tests/` | Tests for the validator and the eval grader |

## Checks

From the repository root:

```bash
uv run --no-project --with pytest --with jsonschema --with pyyaml pytest registry-bridge/tests
uv run registry-bridge/scripts/validate_handoff.py registry-bridge/pilots/household-support-grant/service-handoff.yaml
```

Kestria is a fictional country. Every person, number and institution in the pilot is fictional.
