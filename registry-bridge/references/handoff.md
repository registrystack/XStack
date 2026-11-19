# The service hand-off

A `service-handoff.yaml` is what one chosen XStack design hands to Registry Stack. It records the questions, pages, back office and open items of **one prototype iteration**, at a **level of detail**, and says plainly what it could not find.

It is the only file later skills read. Nothing after it reads XStack's HTML, `assumptions.md` or `form-spec.md` again.

- **Schema:** `handoff.schema.json` (JSON Schema 2020-12)
- **What each level requires for each gap:** `required-from.json`
- **Validate:** `uv run registry-bridge/scripts/validate_handoff.py path/to/service-handoff.yaml`
- **Worked example:** `../pilots/household-support-grant/service-handoff.yaml`

All paths in the file are relative to the repository root.

## Top level

| Field | What it holds |
|---|---|
| `handoff_version` | Always `1` for this contract. |
| `service` | `id` (lower case, hyphens), `name` as the service is called on its start page, and `owner`, the organisation the profile or service sheet names. |
| `level` | `alpha`, `beta` or `live`, the phase names XStack teams already use. See "Levels". |
| `sources` | Where everything came from. See "Sources". |
| `missing_parts` | XStack inputs this design does not have. See "Missing parts". |
| `questions` | Every fact the service uses, one row each. See "Questions". |
| `form_items` | Every item on the paper form, when there is a form spec. Empty otherwise. |
| `pages` | The citizen's pages, in order, with branching. |
| `back_office` | What happens after the citizen presses send, or out of their sight. Never a citizen page. |
| `open_items` | Every tagged assumption in the chosen iteration, with XStack's tags. |
| `gaps` | One row for each of the 13 things Registry Stack needs that XStack does not ask. |
| `unresolved` | Rows the writer could not resolve, each pointing at the row and saying why. |

## Levels

| Level | For | What it asks |
|---|---|---|
| `alpha` | A quick proof of concept | Almost nothing. Every gap can take the starter default. Synthetic data and demo identity. |
| `beta` | A pilot with real users | Every trust-boundary gap is answered. Convenience gaps may stay defaulted, each one listed. |
| `live` | Production | No trust-boundary gap stays defaulted. Each answer names an owner and a source. |

Alpha defaults are less capable, never less safe. Access and data sharing default to the narrowest setting. Only convenience settings, such as demo sign-in, are loose, and a production check refuses them.

`required-from.json` holds, for each gap, what each level requires and whether the gap is on the trust boundary. Which gaps count as trust boundary is a first proposal and will change as pilots test it.

The validator does not apply these level rules. It checks the file's shape and that its rows point at each other correctly. `handoff-to-brief` applies the level rules when it reads the hand-off.

## Sources

| Field | What it holds |
|---|---|
| `xstack_ref` | The XStack commit the design was read at. |
| `profile` | The country profile folder, or `null`. |
| `service_sheet` | The profile's sheet for this service, or `null`. |
| `brief` | The brief the prototypes were built from, or `null`. |
| `prototype` | The one chosen prototype: `name` (its folder), `iteration` (a number, 1 for the folder's own `index.html`), `page` (its `index.html`), `assumptions` (its `assumptions.md`) and `why` (why this one, in a few sentences). |
| `shared_assumptions` | The `assumptions.md` shared by all prototypes, or `null`. |
| `form_spec` | The `form-spec.md`, or `null`. |

A hand-off describes one iteration. Comparing prototypes is XStack's job, before the hand-off.

## Missing parts

Each row names a `part` and a `note`. The parts are `form-spec`, `question-map`, `service-sheet`, `brief`, `data-catalogue`, `personas` and `profile`.

A missing part is not an error. XStack inputs differ from one service to the next: one has a question map and no form spec, another the opposite. Declaring it lets later skills ask for it instead of guessing. When `sources.form_spec` is `null`, `form-spec` must be listed and `form_items` must be empty.

## Questions

One row for each row of XStack's question map, plus any fact the pages ask that the map left out.

| Field | What it holds |
|---|---|
| `id` | For a known or derived fact with a data catalogue key, that key in lower case with hyphens (`hsgAssessment` becomes `hsg-assessment`). Otherwise a short name for the fact. |
| `label` | The question or fact in the service's own words. |
| `map` | `known` (government already holds it and the person confirms it), `derived` (worked out, never asked) or `ask`. Taken from the question map. |
| `attribute` | The data catalogue key, such as `household`, or `null`. A known fact must have one. |
| `source` | The register, and the platform it comes through, as the profile names them. Required for known and derived facts. |
| `fallback` | What the service does when the fact is missing or refused, or `null`. |
| `tags` | XStack's tags on this row: `[VERIFY WITH USERS]`, `[VERIFY WITH POLICY]`, `[VERIFY WITH DEPARTMENT]`, `[VERIFY WITH PLATFORM]`, `[VERIFY WITH DATA]` and `[KNOWN GAP]`. |
| `required_from` | The first level at which this row must come from its real source or a real answer. Known and derived facts are `beta`: at alpha they read synthetic records. Asked facts are `alpha`. |
| `fields` | The names or ids of the prototype's form controls that answer or confirm this fact. Empty for a fact that is only shown. |
| `gaps` | Optional. The numbers of the gaps (below) this row touches. |
| `form_items` | Optional. The form item ids this row covers. |

Lawful basis is never written here as a fact. Where the design states one, it stays an open item with its `[VERIFY WITH POLICY]` tag.

## Form items

Only when there is a form spec. One row for each row of the spec's coverage check: the form's own `id` (such as `5(a)`), `paper_asks` in the form's words, and the spec's digital treatment as `category`: `ask`, `lookup`, `lookup-opportunity`, `conditional`, `add-another`, `government-holds`, `drop-or-challenge` or `back-office`. `question` links it to a question row.

## Pages

In the order the prototype's HTML has them. Each page has:

| Field | What it holds |
|---|---|
| `id` | The prototype's page id without its prefix (`page-confirm-you` becomes `confirm-you`). |
| `title` | The page heading. Where the heading is filled in at runtime, the prototype's default. |
| `kind` | `start`, `question`, `confirm` (shows held facts to check), `notice`, `interruption` (sign-in failed, record not found), `outcome`, `check-answers`, `confirmation` or `exit` (the journey ends without applying). |
| `section` | Optional. The section tag the page shows, such as "About you". |
| `asks` | Questions answered on this page. |
| `shows` | Questions whose held or derived value is shown on this page, with its source. |
| `next` | Where the page can lead. Each branch has `to`, an optional `when` in plain words, and an optional `via` for a step outside the service, such as a sign-in or a record lookup. An empty list ends the journey. |
| `submits` | `true` on the page that sends the application. Exactly one page has it. |

Every page must be reachable from the first page through `next`. Stub pages ("not built yet") are left out and listed as an open item.

## Back office

Work the service implies but the citizen never sees: a decision, a visit, a check by hand, a message, a payment. Each row has `id`, `what`, `trigger` (what starts it), `owner`, and optional `tags` and `gaps`. Back-office ids are never used in a page's `asks` or `shows`, and never the same as a question id.

## Open items

One row for each tagged line in the chosen iteration's `assumptions.md`, in the order they appear, numbered `oi-1`, `oi-2` and so on. Each row keeps the line's `tags`, gives a short `text` in plain words, and a `concern`:

- `service`: the service's own design or policy
- `platform`: depends on how a national platform behaves
- `prototype`: an artefact of the prototype or its mock only
- `design-system`: a missing or conflicting component
- `language`: translation and language support

`severity` (`high`, `medium`, `low`) is optional, for when the source gives one. `refs` can point at other rows.

## Gaps

Exactly one row for each gap in `required-from.json`, by `id` (1 to 13). `status` says what the design gives:

- `designed`: the XStack design answers it, perhaps with tags still open
- `default`: the design is silent, so the starter default applies at this level
- `open`: the design knows it matters but leaves it out, often as a `[KNOWN GAP]`

`note` says what the design says or leaves out. `refs` points at the rows that show it.

## Unresolved

Anything the writer could not settle from the inputs: a fact with no source, a branch it could not follow, a tag it could not place. Each row has a `ref` such as `questions/nearest-csc` and a `reason`. A hand-off with unresolved rows is still valid. Hiding them is not.

## References

`ref` values are `section` or `section/id`, where section is one of `questions`, `pages`, `back_office`, `open_items`, `form_items`, `gaps` or `sources`. The validator checks each one points at something real.
