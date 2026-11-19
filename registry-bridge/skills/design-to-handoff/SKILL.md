---
name: design-to-handoff
description: Turn one chosen XStack prototype iteration into a validated service-handoff.yaml for building the service on Registry Stack. Reads the prototype's index.html, its assumptions.md (question map and tagged assumptions), the shared assumptions.md, any form-spec.md, and the country profile's dpi.md and service sheet. Writes questions (known, derived or ask), ordered pages with branching, back-office rows, open items, the 13 Registry Stack gaps at a level (alpha, beta or live), and flags every row it could not resolve. Use when a team has finished designing with XStack and wants to implement on Registry Stack, or asks for a "hand-off", "service hand-off", "design to Registry Stack" or "/registry-bridge:design-to-handoff". Not for building, iterating or hardening the HTML prototype (that is xstack:brief-to-prototypes, xstack:iterate or xstack:build-for-production), and not for turning a paper form into a spec (that is xstack:form-to-spec).
---

# Design → hand-off

This skill reads what XStack made for one service and writes one file, `service-handoff.yaml`, that Registry Stack skills build from. It is the only skill in `registry-bridge` that reads XStack's file formats. Everything later reads the hand-off.

The contract is `references/handoff.md` and `references/handoff.schema.json` in this plugin. Read `handoff.md` before you start. The worked example is `pilots/household-support-grant/service-handoff.yaml`.

**Faithful, not creative.** The hand-off records what the design says. It does not improve the journey, settle a `[VERIFY WITH …]` tag or fill a gap from memory. Where the design is silent or unclear, write what you can and add an `unresolved` row. A short honest hand-off is better than a complete invented one.

---

## Before you start

This skill needs only the XStack files and `uv` (to run the validator). It does not need Registry Stack installed. Later `registry-bridge` skills do, and some of the Registry Stack repositories they need are not public yet.

**Gather the inputs.** Paths are relative to the project root.

| Input | Where XStack puts it | Required |
|---|---|---|
| The chosen prototype page | `<build>/prototype-N-<name>/index.html`, or `.../iteration-K/index.html` | Yes |
| Its assumptions | `assumptions.md` next to that page | Yes |
| Shared assumptions | `<build>/assumptions.md` | If it exists |
| Form spec | `form-spec.md` | If it exists |
| Brief | `<build>/brief.md` | If it exists |
| Country profile | `.xstack/profile.md` or a bundled `profiles/<country>/` | If it exists |
| Data catalogue | `dpi.md` in the profile | If it exists |
| Service sheet | `services/<service>.md` in the profile | If it exists |

**Choose one prototype and one iteration.** If the user names them, use those. If not, ask, and offer the latest iteration of each prototype with its hypothesis from the build's README. Never merge prototypes: a hand-off describes one journey. The iteration is the number in the `iteration-K` folder, or `1` for the prototype folder's own `index.html`. Write a few sentences in `sources.prototype.why`: why this one, and what the other prototypes would have needed.

**Choose the level.** `alpha`, `beta` or `live`. If the user doesn't say, use `alpha` and say so.

**Record the XStack commit** in `sources.xstack_ref` (`git rev-parse --short HEAD` in the XStack checkout, if there is one; otherwise ask).

## Step 1 – Missing parts

For each input above that does not exist, add a `missing_parts` row with a one-line note. When there is no form spec, `sources.form_spec` is `null`, `form-spec` is listed, and `form_items` is empty. Check the shared `assumptions.md` too: XStack often says there why a part is missing ("No form spec").

## Step 2 – Questions

Read **both question maps**: the one at the top of the iteration's `assumptions.md` and the one in the shared `assumptions.md`. The iteration's map wins where they disagree, because it is newer. Keep a shared-map row the iteration's map leaves out unless the iteration says it was dropped, and keep the tags from both. If neither has a map, add `question-map` to `missing_parts` and build the questions from the pages (step 4).

One row per fact in the question maps. Then add a row for each thing a page asks that the maps left out, for example:

- a routing question, such as "Do you have a digital ID?"
- a **fallback question**: what a page asks when a known fact is missing, refused or wrong, such as "How many people live in your household?" or "How should we pay you?". This is its own `ask` row, not part of the known fact, because one is confirmed and the other is typed in. Name it in the known fact's `fallback`.

- **`id`:** for a fact with a data catalogue key, the key in lower case with hyphens (`payoutAccount` → `payout-account`). Otherwise a short name for the fact in the same style.
- **`map`:** `known`, `derived` or `ask`, as the question map says.
- **`attribute`:** the data catalogue key the page reads, **only if it is in the profile's `dpi.md` data catalogue**. Check each one. A known fact must have one. If the design reads something the catalogue does not list, write `null` and add an `unresolved` row.
- **`source`:** the register and the platform it comes through, in the profile's names.
- **`fallback`:** what the question map, or the page logic, does when the fact is missing or refused.
- **`tags`:** the tags on the question map row, and any tag the iteration's assumptions put on that fact.
- **`fields`:** every form control (`name` or `id` in the HTML) that confirms or answers this fact. For a known fact, the controls that confirm it and those that type in the same fact on the route without records (such as name and phone). Controls of a fallback question belong to that question. Empty when the fact is only shown.
- **`required_from`:** `beta` for known and derived facts, `alpha` for asked facts (see `handoff.md`).
- **`gaps`:** optional, the gap numbers the fact touches.

Never write a lawful basis as a fact. If the design states one, it stays an open item with its tag.

## Step 3 – Form items

Only with a form spec. One row per row of the spec's section 10 coverage check, with the form's own id, the "Paper asks" words, and the digital treatment as `category`. Link each to its question.

## Step 4 – Pages

Read the page sections of the prototype's `index.html` in document order (XStack prototypes use `<section id="page-…">`).

- **`id`:** the section id without `page-`. Leave out stub pages ("Not built yet") and list them as an open item if `assumptions.md` hasn't already.
- **`title`:** the `h1`. If script fills it in, use the default in the HTML or the most common case.
- **`kind`:** see `handoff.md`.
- **`section`:** the section tag above the heading, if there is one.
- **`asks`:** questions whose `fields` are on this page.
- **`shows`:** questions whose held or derived value the page shows (summary rows, "From government records", outcome text).
- **`next`:** read the page's submit handler and buttons. Each `goTo`, `show` or link to another page is a branch. Write `when` in plain words from the condition. When the step goes through sign-in or a record lookup first, put that in `via` and point `to` at the page the person lands on.
- **`submits`:** `true` on the page whose button sends the application.

## Step 5 – Back office

List what the design says happens out of the citizen's sight: decisions, visits, checks by hand, messages, payments, changes made at an office. Take them from the outcome and confirmation pages, the service sheet, and the assumptions. Each row has `what`, `trigger`, `owner`, and the tags it carries. A back-office row never appears in a page's `asks` or `shows`.

## Step 6 – Open items

One row for every tagged line in the **iteration's** `assumptions.md` (lines that start with a tag, such as ``- `[VERIFY WITH POLICY]` ``), in the order they appear, numbered `oi-1`, `oi-2` and so on. Keep every tag on the line. Write `text` as a short summary in plain words. Choose `concern`: `service`, `platform`, `prototype`, `design-system` or `language`.

Don't add untagged lines, and don't drop resolved-looking ones: if the line is tagged, it is an open item. Say in `text` when a later iteration has resolved part of it.

## Step 7 – Gaps

Read `references/required-from.json`. Write exactly one row for each of the 13 gaps:

- `designed` when the design answers it, even with tags still open
- `default` when the design is silent, so the starter default applies at this level
- `open` when the design knows it matters but leaves it out, usually a `[KNOWN GAP]`

`note` says in a sentence what the design gives or leaves out. `refs` points at the rows that show it.

## Step 8 – Unresolved

Add a row for every fact without a source, every branch you could not follow, every attribute not in the catalogue, and anything else you had to guess. Point `ref` at the row and say why in `reason`.

## Step 9 – Validate and report

Write the file (`.xstack/service-handoff.yaml` unless the user names a path), then run the validator from this plugin:

```bash
uv run <registry-bridge>/scripts/validate_handoff.py path/to/service-handoff.yaml
```

Fix every error and run it again until it says `valid`. The usual errors are YAML ones: quote any value that is `yes`, `no`, `on` or `off`, or that holds a comma inside `{ … }`, or YAML reads it as a boolean or a new key.

Then tell the user, briefly:

- which prototype and iteration, at which level
- how many questions, pages, back-office rows and open items
- the missing parts
- the gaps by status
- every `unresolved` row, in full

Don't edit XStack's files, and don't write anything for Registry Stack yet. The next step is `handoff-to-brief`, when it exists.
