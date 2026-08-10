# Tessera v2 — Data & Schema Change Plan (corrected)

Source of truth for target scope: `vedha_tessera_model_v2.html`.
Source of truth for current state: **`simulation.py` + `schema/clickhouse_ddl.sql`** (the actual generator and DB — not `entities.yaml`/`activities.yaml`, which have already drifted out of sync with the real code; see §0).

**Ground rule from the user, applied throughout this plan:** this codebase never stores metric formulas. `entities.yaml`/`activities.yaml`/`config.py`/`simulation.py` only define entities, columns, and activities — raw data. Metrics (Goal/Drivers/Inputs/Guardrails in the HTML) are computed later, by querying that raw data. So for every metric in the HTML, this plan asks one question only: **do we already have the columns to compute it via a query, or do we need to add/change a column or entity?** No formula gets written into the codebase — only the raw fields required to make the formula answerable downstream.

Nothing in this plan has been implemented.

---

## 0.0 Explicit guarantees for this plan (confirmed with the user)

These are the four commitments this plan is designed to satisfy end to end. Each is tied to the section that implements it, plus the one caveat attached to it — flagged so nothing turns up missing after implementation.

1. **Every metric in the HTML becomes computable, across all 8 workflows.** §3–§6 add the raw columns/entities each metric is currently missing. **One caveat**: `Elasticity ε` and `Price-to-value (WTP)` in Monetisation have no real-world signal to derive from in a simulation — they become computable only because we *define* a price-response relationship ourselves when generating the data (a synthetic input, decided in §7 Q3), not because we discover it from otherwise-neutral data. Every other metric is a genuine derivation from raw facts.
2. **Weekly grain, everywhere, not just Functional.** Achieved by the design rule: *every table — existing or new — stores a real timestamp/date, never a pre-aggregated month bucket.* Where that rule already holds (`usage_event`, `support_ticket`, `expansion_opportunity`, `contract`, `visitor`, `health_score_snapshot`), weekly is already free via query. Where it doesn't (`cohort`, `campaign`), §4.2 adds it. The same rule will be applied to every new table in §3 (Cost & Burn, MRR movement, P&L) so they're weekly-queryable too. **One caveat**: real-world cost/headcount data (payroll, vendor invoices) is naturally monthly — a weekly cost figure will be an even/weighted allocation of the monthly number, not an independently observed weekly value. That's noted explicitly in §3.2/§4.2 so it's not mistaken for organic weekly data. Note also that the HTML itself only *requires* weekly cadence at the Functional altitude (Company=monthly, Financial=monthly·quarterly) — going weekly everywhere is extra capability beyond what the recipe asks for, not a contradiction of it.
3. **September gets the same generation pattern as every other month, not a stub.** §4.1 extends every hardcoded month-count/weight list (`MONTH_RANGE`, `ACCOUNT_MONTHLY_WEIGHTS`, the health-score week range, `generate_plan()`'s end bound) by exactly one month, continuing the existing taper in `ACCOUNT_MONTHLY_WEIGHTS` rather than adding a special-cased partial month. `validate_all()`'s `expected_months` check gets bumped 20→21 specifically so a sparse September would fail validation automatically, not slip through silently.
4. **Naming and dimension values become consistent with the HTML everywhere.** §1/§2 give the exact rename/add mapping for every entity, activity, and dimension. The five open questions this depended on are now resolved — see §7 — so §1/§2 reflect final decisions, not placeholders.

---

## 0. Housekeeping — the YAML docs are already out of date

`entities.yaml` / `activities.yaml` describe a schema that no longer matches `simulation.py`. Examples:

| File says | Code/DB actually has |
|---|---|
| `Contract.mrr_usd`, `.arr_usd` | `contract.mrr`, `contract.arr` (`simulation.py:603-604`, `clickhouse_ddl.sql:176-177`) |
| `ExpansionOpportunity.opportunity_id`, `.opportunity_type`, `.stage`, `.expansion_mrr_potential` | `expansion_opportunity.opp_id`, `.trigger_type`, `.upsell_status`, `.expected_mrr_uplift` (`simulation.py:855-871`) |
| Activities `plan_upgraded` / `plan_downgraded` declared | **Never actually generated anywhere** — `account.current_plan_id` is static for the whole simulation; there is no upgrade/downgrade event log |
| `Account.country`, `.region`, `.icp_segment` | `account.geo`, `.region`, `.segment` (`simulation.py:274-276`) |

**Step 1 of implementation must be**: regenerate `entities.yaml` and `activities.yaml` from the real code (or drop them if they're not load-bearing anywhere) so the docs stop lying about what data exists. Every section below is grounded in the real columns, not the stale YAML.

---

## 1. Terminology alignment — entities & activities, by workflow

For each workflow: HTML name → what exists today (real column/table) → what needs to change. "Add" = new column/entity needed. "Rename" = data already exists, just under a different name. "Missing" = concept doesn't exist at all yet.

### Acquisition
| HTML | Today | Action |
|---|---|---|
| Entity `Visitor` | `visitor` table | keep (name matches) |
| Entity `Campaign` | `campaign` table | keep |
| Entity `Signup` | `visitor.did_signup` (bool) + `visitor.converted_user_id` | **add**: promote to a real event/flag with a timestamp, not just a boolean |
| Entity `Channel` | `campaign.channel` / `visitor.channel` (free string) | keep as attribute, but **rename values** (see §2) |
| Entity `Creative` | doesn't exist | **add**: new entity (ad/creative variant under a Campaign) |
| Activity `impression`, `click` | only aggregate `campaign.impressions`/`.clicks` (month totals) | **add**: no event-level impression/click rows exist |
| Activity `LP visit` | `visitor.lp_url` (attribute, not an event) | keep as attribute — already captures this, no change needed |
| Activity `qualify` | doesn't exist | **add**: no qualify flag/step anywhere |

### Activation
| HTML | Today | Action |
|---|---|---|
| Entity `New user` | `user` table | keep (rename is cosmetic only) |
| Entity `Onboarding step` | `usage_event.onboarding_step_name` (free string, `ONBOARDING_STEPS` = `dashboard_viewed`, `team_member_invited`, `integration_connected`, `workflow_created`, `data_imported` — `config.py:221-227`) | **rename + restructure**: current step names don't map to spec's `setup → connect → integration → first action → invite → reach value`; also currently one flat list with no fork by motion |
| Entity `Value-moment` | doesn't exist (`user.activated_at` is the closest proxy) | **add**: explicit value-moment flag/timestamp, distinct from generic activation |
| Entity `Cohort` | `cohort` table | keep |
| Activity fork by motion (self-serve PLG path vs. sales-led CS-guided path) | single flat onboarding sequence, no fork | **add**: two distinct step sequences gated by a `motion` value |

### Retention
| HTML | Today | Action |
|---|---|---|
| Entity `Usage event` | `usage_event` table | keep |
| Entity `Health score` | `health_score_snapshot` table | keep |
| Entity `Core/Power user` | `Core`/`Power` exist only as **unused dead keys** in `EVENTS_PER_MONTH` (`config.py:236-237`) — no account or user is ever actually assigned these states; real lifecycle values come from `LIFECYCLE_STATE_WEIGHTS` (`Active`, `Churned`, `Reactivated`, `Trial`, `Suspended`, `Qualified` — `config.py:177-184`) | **add**: Core/Power tiering is not implemented, it's a dangling config reference |
| Entity `Renewal` | exists only as a second `contract` row generated in `generate_contract()` (`simulation.py:616-638`), owned by Monetisation | **move/tag**: needs to be attributable to Retention, not just a Contract-table side effect |
| Activity `QBR` | doesn't exist | **add** |
| Activity `login` | not distinct from `usage_event` — session tracked via `session_id`, no discrete login event | **add** (or explicitly decide session_id already covers it) |

### Expansion
| HTML | Today | Action |
|---|---|---|
| Entity `Expansion opp` | `expansion_opportunity` table | keep (field names differ, see §0 table) |
| Entity `Seat` | `seat` table | keep |
| Entity `Team` | doesn't exist | **add** |
| Entity `Add-on` | only `contract.addon_mrr` (a number, Enterprise-only, no catalog) | **add**: proper add-on catalog entity |
| Activity `seat add`, `tier upgrade`, `add-on buy`, `hit limit`, `upsell convo` | collapsed into `expansion_opportunity.trigger_type` (a categorical field with values like `limit_hit`, `tier_upgrade`) and before/after seat counts on the same row | **add**: these need to be discrete event rows, not values baked into one opportunity record |

### Monetisation
| HTML | Today | Action |
|---|---|---|
| Entity `Contract` | `contract` table | keep |
| Entity `Plan/Tier` | `plan` table (already SCD-2: Plus v1 $12 → v2 $15, `config.py:34-58`) | keep — this already does part of what "Price book" is meant to do |
| Entity `Price book` | folded into `plan.list_price_per_seat` | **resolved — keep folded into `Plan`**, no new entity. Only change: documentation/labels reference it as "Price book" where the HTML's terminology is relevant, so the naming matches even though the structure doesn't change |
| Entity `Discount` | only `contract.discount_pct` (scalar, set once at contract creation) | **add**: no discount-grant event log, just a static field |
| Entity `Add-on` | shared gap with Expansion above | **add** |
| Activity `price change`, `tier change`, `discount grant`, `add-on attach`, `renewal pricing` | none exist as discrete events | **add**: all currently invisible, baked into static fields set once |

---

## 2. Dimension naming & member-value alignment

The HTML's "Dimensions dictionary" (bottom of the file) is the naming standard to match. Members marked *(illustrative)* in the HTML are placeholders the spec author flagged as unconfirmed — treat those as open questions, not hard requirements.

### Shared dimensions
| HTML dimension | HTML values | Today | Action |
|---|---|---|---|
| `segment` | SMB, Mid-market, Enterprise | `account.segment`: SMB, Mid-Market, Enterprise | **rename**: `Mid-Market` → `Mid-market`, exact casing per the HTML (was previously left as "trivial casing only" — not actually identical until this rename happens) |
| `plan / tier` | Free, Plus, Business, Enterprise | `plan.tier`: same | keep — matches |
| `motion` | Self-serve, Sales-led | **not a unified dimension anywhere.** Scattered as `account.is_self_serve` (bool) and `expansion_opportunity.motion_type` (`plg_inapp`/`sales_assist`) | **add**: one `motion` column storing the literal strings `Self-serve` / `Sales-led` — matching the HTML's exact display text, not snake_case internal codes (corrected from an earlier draft of this plan that proposed `self_serve`/`sales_led`, which would have broken exact-match). Applied across Acquisition, Activation, Monetisation, Revenue engine — not just Expansion |
| `cohort` | signup-period buckets, weekly or monthly | `cohort.cohort_grain` hardcoded to `'monthly'` (`simulation.py:308`) | **add**: weekly grain option |
| `geo` | NA, EMEA, APAC, LATAM *(illustrative)* | `account.region` / `GEOS`: North America, Europe, APAC, LATAM (`config.py:127-140`) | **resolved — label rename only**: North America→NA, Europe→EMEA, adopted exactly as the HTML names them. No change to which countries are actually modeled (still Europe-only under the EMEA label) — this is a naming rename, not a geographic-coverage expansion |
| `period` | week, month, quarter, year | `time_period` string, month-grain only, on every table | **add**: real date columns already exist on most tables (so week/quarter/year are derivable via query) — the exception is snapshot-style tables that only ever had a month bucket (see §4) |

### Workflow-local dimensions
| HTML dimension | HTML values | Today | Action |
|---|---|---|---|
| `channel` | Paid, Organic, Referral, Direct | `CHANNELS`: paid_search, content_seo, direct, product_led, field_sales (`config.py:121`) | **resolved — remap to exactly these 4 values**: paid_search→Paid, content_seo→Organic, direct→Direct. `product_led` and `field_sales` are not channel values in the HTML's taxonomy — they get reclassified as `Direct` channel + the new `motion` dimension (`Self-serve` / `Sales-led`) carrying that distinction instead. `Referral` has **no generator today producing it** (zero referral-sourced visitors exist currently) — this needs actual new generation logic (a referral traffic source), not just a label; without it, `Referral` would exist in the taxonomy but never appear in a real row |
| `account size` | <10 seats, 10–50, 50–200, 200+ *(illustrative)* | `account.account_size_band`: small/medium/large — **but this is just a 1:1 relabel of `segment`**, not an independent measure (`SEGMENT_SIZE_BAND`, `simulation.py:61`) | **resolved — add**: real seat-count-derived band, computed from actual seat/contract counts, decoupled from segment. Bucket edges use the HTML's exact numbers (<10, 10–50, 50–200, 200+) as the banding thresholds |
| `health band` | Green, Yellow, Red | `health_score_snapshot.health_band`: red/amber/green (lowercase) | **rename**: capitalize, and amber→Yellow |
| `industry` | SaaS/Tech, Financial svcs, Healthcare, Retail, Other *(illustrative)* | `INDUSTRIES`: 10 granular verticals (`config.py:144-149`) | **resolved — replace outright.** The 10-value list is dropped; `INDUSTRIES` becomes exactly the HTML's 5 values. Weights across the 5 aren't specified by the HTML, so new `INDUSTRY_WEIGHTS` get defined as a reasonable distribution (skewed toward SaaS/Tech, consistent with the current data's skew) — flagged here as an assumption, not a value taken from the spec |
| `utilisation band` | <50%, 50–80%, 80–100%, at limit | doesn't exist — only a categorical trigger value `utilization_high` among five trigger types | **resolved — add**: real `seat_utilisation_pct` + banding, using the HTML's exact bucket edges |
| `deal size` | <$5k, $5–25k, $25–100k, $100k+ ACV *(illustrative)* | doesn't exist | **resolved — add**: `deal_size_band` derived from `contract.arr`, using the HTML's exact bucket edges |
| `cost line` | Cloud & infra, AI inference, People, Other | doesn't exist at all | **add** — part of Cost & Burn build |
| `function` | R&D, S&M, G&A, CS *(illustrative)* | doesn't exist for cost centres (`user.department` is a different concept — engineering/product/etc. per employee, don't conflate) | **add**: new cost-centre function field |
| `space` | Acquisition, Activation, Retention, Expansion, Monetisation | doesn't exist | **add** — needed on the new MRR movement bridge (§3.3) |

**On using the HTML's illustrative numbers for banding**: `account size`, `deal size`, and `utilisation band` all need a categorical value written onto each row (e.g. `account_size_band = '10-50'`) — that's raw dimension data, same as `segment` or `plan_tier` already are. The HTML's numeric edges get used only to decide where one band ends and the next begins when the generator writes that categorical value. This is not the same thing as adding a metrics-calculation module to the codebase — no formula, ratio, or rollup gets computed or stored; it's strictly "which bucket does this row's continuous value fall into," exactly like the existing `SEGMENT_SIZE_BAND` mapping already does today.

---

## 3. New workflows — what raw data is missing, metric by metric

### 3.1 Financial — P&L *(nothing exists today)*
No revenue-line, cost-centre, or cash data exists anywhere in the current tables. Every metric here (`Net Profit`, `Revenue`, `Cost`, `Gross Margin`, `Runway`, `Rule of 40`) is **not computable** until Cost & Burn (§3.2) exists.

**Resolved: no dedicated `p_and_l` table.** `Net Profit`, `Gross Margin`, and `Rule of 40` are pure `Revenue − Cost` derivations over Revenue engine (`mrr_movement`) + Cost & Burn (`cost_centre`) — storing them in their own table would mean storing a computed metric result as a row, which the ground rule in §0 rules out. Same pattern the Revenue engine already follows: `mrr_movement` stores raw movement facts; ARR/NRR/GRR are computed from it at query time, never pre-stored.

That said, two pieces of genuinely missing **raw data** remain regardless of table structure:
- **`revenue_line`** — `Revenue = MRR×12 (recognised) + services`. The "services" component doesn't exist anywhere today; every dollar in the current data is subscription MRR. Without a raw record of non-subscription revenue, this formula can't be computed by any query. Missing data, not a missing formula.
- **`cash`** — `Runway = Cash / Burn`. Cash is a stock, not a flow — it needs an opening balance plus period deltas tracked as state (the same pattern `account.lifecycle_state` already uses), because it isn't recoverable purely from Revenue-minus-Cost inside the simulation window without knowing the starting position.

### 3.2 Company — Cost & Burn *(nothing exists today)*
No cost data of any kind exists in the current schema. New tables needed: `cost_centre`, `vendor`, `headcount`, and cost-line-tagged spend rows (`cost line` = Cloud & infra / AI inference / People / Other, `function` = R&D/S&M/G&A/CS). Every metric here (`Burn vs plan`, `Gross Margin`, `Runway`, `Cost-to-serve`) is currently **not computable** — this blocks several Acquisition/Revenue-engine metrics downstream too (CAC payback, LTV:CAC, Burn multiple all need GM, which needs COGS from here).

### 3.3 Company — Revenue engine *(the MRR waterfall doesn't exist)*
| Metric | Computable today? | What's missing |
|---|---|---|
| `MRR = Active Paid Seats × ARPU`, `ARR = MRR×12` | Partially — `contract.mrr`/`.arr` already exist as point-in-time values | The seats×ARPU *identity* (i.e. deriving MRR bottom-up from a seat count and ARPU) isn't reconcilable, because seats and MRR aren't tracked as a joint waterfall |
| `Active Paid Seats(t) = Seats(t-1) + New + Reactivated + Expanded − Churned − Contracted` | **No** | No `MRR movement` bridge table exists — nothing records period-over-period seat/MRR movement by type |
| `ARPU = base×(1−discount) + add-on/seat + tier premium` | Partially — `contract.realized_price_per_seat` exists | No add-on/tier-premium decomposition; add-on MRR isn't broken out per seat |
| `NRR`, `GRR` | **No** | Both require the MRR movement bridge above, split into Start/Churn/Contraction/Expansion — none of these categories currently exist as distinct, joinable fields |

**Add**: `mrr_movement` fact table (one row per account per period per movement type: new/reactivate/expand/contract/churn/renew), tagged with `space` (which functional workflow drove it). This is the single highest-leverage new table — it's what makes NRR/GRR/Net New MRR/Burn multiple all computable at once.

### 3.4 Monetisation — synthetic WTP/elasticity (resolved: add it)
There's no real-world signal for `Elasticity ε` or `Price-to-value (WTP)` in a simulation — they only become computable because we choose a price-response relationship ourselves. Concrete design:
- **`ELASTICITY_BY_SEGMENT`** — a new config constant, one coefficient per segment (e.g. SMB most price-sensitive, Enterprise least), analogous to the existing `DISCOUNT_BY_SEGMENT` pattern already in `config.py:283-287`.
- **`account.willingness_to_pay_usd_per_seat`** — a new synthetic column, drawn per account from a segment-level mean plus noise, so WTP-vs-price comparisons are queryable per account.
- **More than one price-change data point** — today there's exactly one real price change in the data (`Plus` $12→$15, `config.py:34-58`), which is too thin to observe any elasticity response from. Add at least one more SCD-2 price version on a different tier so a before/after comparison exists on more than a single tier.

This stays inside the "raw data only" ground rule — `ELASTICITY_BY_SEGMENT` and `willingness_to_pay_usd_per_seat` are inputs the generator consumes to produce realistic contract/discount behavior, not a stored formula for "elasticity" itself.

---

## 4. Time coverage & grain — extend to September, add weekly

### 4.1 Extend the simulation window through September 2026
Everything is currently hardcoded to stop at August 2026:
- `SIM_END = datetime(2026, 8, 31, 23, 59, 59)` (`config.py:11`)
- `MONTH_RANGE = pd.date_range('2025-01-01', '2026-08-01', freq='MS')` — 20 months (`simulation.py:49`)
- `ACCOUNT_MONTHLY_WEIGHTS` — exactly 20 weights, one per month (`config.py:303-308`)
- `generate_plan()`'s `sim_end_month = pd.Timestamp('2026-08-01')` (`simulation.py:142`)
- Health-score week range `pd.date_range('2025-01-06', '2026-08-25', freq='W-MON')` (`simulation.py:904`)

**Changes needed**: push every one of these bounds out by one month (21 months total, through September 2026), and add a 21st weight to `ACCOUNT_MONTHLY_WEIGHTS` (renormalize so weights still sum to 1). Also grep the whole codebase for any other literal `2026-08` reference to make sure nothing else silently caps at August.

**On "not just 1-2 days of that month"**: nothing in the generator reads today's real-world date — all bounds are fixed literals — so there's no live "truncate at today" bug today. The actual risk is when *extending* to September: if the new month's weight/range isn't wired through everywhere above, September could end up sparsely populated (e.g. only a few early-month rows) while every other month is fully populated across all ~30 days. The fix is to treat September exactly like every other month in `MONTH_RANGE`/`ACCOUNT_MONTHLY_WEIGHTS`/the health-score week list — not a special partial case — and validate row counts per month are comparable after generation (the existing `validate_all()` in `simulation.py:983` already checks month coverage — extend `expected_months` from 20 to 21 there too).

### 4.2 Add weekly grain — but only where the HTML actually asks for it
The HTML's own "clock" per altitude differs (line 119, 156, 217 in the spec):
- Financial: monthly · quarterly
- Company: monthly
- **Functional: weekly → quarterly**

So weekly grain is only required at the Functional altitude (Acquisition/Activation/Retention/Expansion/Monetisation), not Company/Financial. Auditing what's already weekly-capable vs. not:

| Table | Has real timestamps already? | Weekly-queryable today? |
|---|---|---|
| `usage_event`, `support_ticket`, `expansion_opportunity`, `contract`, `visitor` | Yes (`occurred_at`, `opened_at`, `identified_at`, `start_at`, `first_seen_at`) | **Yes** — weekly buckets are already derivable via query (e.g. `toStartOfWeek(...)`); no schema change needed |
| `health_score_snapshot` | Yes — already generated at `week_start` grain (`simulation.py:887-969`) | **Already weekly** — this is the one table already matching the spec's cadence, no change needed |
| `cohort` | No — one row per channel per **month** only, `cohort_grain` hardcoded `'monthly'` | **No** — needs a parallel weekly cohort grain added so Activation cohorts can be sliced weekly per the spec |
| `campaign` | No — 4 rows generated per month with the whole month's impressions/clicks/spend pre-aggregated into one number | **No** — weekly CAC/CTR/CPC can't be computed because spend/impressions/clicks are already summed to month level before being written; needs weekly campaign-performance rows instead of (or in addition to) monthly |

---

## 5. Can we compute the HTML's metrics from what we'd have? (data-sufficiency check)

Per the ground rule in §0 — no formulas get stored in code, this only checks raw-column sufficiency.

**Already computable today, no schema change needed:**
- Activation: `Time-to-Value` (`user.signup_at`, `.activated_at` both exist), `Cohort variance` (`cohort.activation_rate` exists per cohort)
- Retention: `Health score` itself (already generated), `Cost-to-serve = accounts/CSM` (`account.csm_owner_id` + `dim_csm`)
- Expansion: `Time-to-expand` (joinable via `expansion_opportunity.closed_at` + `user.activated_at`), `Upsell acceptance` (approximable via `.outcome`)
- Monetisation: `ARPU` (`contract.mrr`/seat_count), `Price realisation` (`contract.realized_price_per_seat` vs `plan.list_price_per_seat`)

**Blocked today — need the additions above before they're computable:**
- Acquisition: `New Qualified Customers`, `CAC`, `Payback`, `LTV:CAC` — all blocked on the missing `qualify` flag and/or Cost & Burn's GM
- Activation: step-wise `Activation Rate = Π r_i` — blocked on defined, ordered onboarding steps (currently only an overall ratio exists, not per-step)
- Retention: `GRR`, `NRR` — blocked on the MRR movement bridge (§3.3)
- Expansion: `Net Expansion MRR`, `Seat utilisation` — blocked on missing contraction-MRR tracking and a "seats purchased vs. seats used" distinction
- Monetisation: `Elasticity ε`, `Price-to-value (WTP)` — blocked; elasticity has only one real price-change data point today (Plus $12→$15) which is too thin to fit a curve, and WTP has no underlying signal at all — this needs a genuinely new synthetic input, not just a derived field
- Revenue engine / Cost & Burn / P&L: everything — all blocked on net-new tables

---

## 6. Step-by-step implementation order

1. **Regenerate `entities.yaml`/`activities.yaml` from the real code** (or retire them) so they stop documenting a schema that doesn't exist (§0).
2. **Rename/replace existing columns/values** for terminology alignment (§1, §2, §7): `geo` region labels, `health_band` casing, `channel` remap, `motion` unification, and the `INDUSTRIES` outright replacement (10 values → the HTML's 5).
3. **Extend the time window** to September 2026 across every hardcoded bound (§4.1), rerun, and confirm `validate_all()` shows 21 months everywhere.
4. **Add weekly grain** to `cohort` and `campaign` (§4.2) — the two tables that don't yet support the Functional altitude's weekly clock.
5. **Build the `mrr_movement` bridge table** (§3.3) — highest leverage single addition, unlocks NRR/GRR/Net New MRR everywhere downstream.
6. **Build Cost & Burn** (`cost_centre`, `vendor`, `headcount`) (§3.2) — unlocks GM-dependent metrics in Acquisition and Revenue engine.
7. **Build the P&L rollup** (§3.1) — depends on 5 and 6 being in place.
8. **Fill the remaining Functional-workflow gaps**: Acquisition `qualify`/`Signup`/`Creative`/a real `Referral`-channel traffic source (§2), Activation motion-forked onboarding steps + `Value-moment`, Retention `Core`/`Power`/`QBR`/`Renewal` ownership, Expansion `Team`/`Add-on`/discrete activity events, Monetisation `Discount`/`Add-on`/pricing-change events + synthetic WTP/elasticity inputs (§3.4).
9. **Add the illustrative-value banding columns** (`account_size_band`, `deal_size_band`, `utilisation_band`) using the HTML's bucket edges (§7 decision 5).
10. **Update `schema/clickhouse_ddl.sql` and `load_to_clickhouse.py`** to match every new/changed table, and re-run the full pipeline end to end.

---

## 7. Decisions (resolved with the user)

1. **Industry taxonomy** — replace outright. `INDUSTRIES` becomes the HTML's 5 values; new weights assumed reasonably since the HTML doesn't specify them (§2).
2. **Price book** — no new entity. Stays folded into `Plan`; only the terminology used to refer to it (docs/labels) matches the HTML's "Price book" language (§1).
3. **Elasticity / WTP** — add synthetic WTP. Implemented via `ELASTICITY_BY_SEGMENT` + `account.willingness_to_pay_usd_per_seat` + at least one additional price-change data point (§3.4).
4. **`geo` region rename** — adopt the HTML's naming as-is (North America→NA, Europe→EMEA), label rename only, no change to which countries are modeled (§2).
5. **Illustrative dimension values** — use the HTML's placeholder numbers as-is for the banding thresholds (`account size`, `deal size`, `utilisation band`). These become categorical column values written by the generator, not metrics/formula code (§2, closing note).

No open questions remain.

---

## 8. File-by-file change list

Everything above describes *what* changes; this section pins down *where*, so implementation isn't left to interpret it. Grounded in the actual current file contents (not the stale YAML).

### `config.py`

**New constants to add:**
- `MOTION_TYPES = ['Self-serve', 'Sales-led']` + a weight/assignment rule (§2)
- A referral-traffic parameter (e.g. `REFERRAL_WEIGHT`) — needed because `Referral` is a channel value with no generator behind it today (§2)
- `COST_LINES = ['Cloud & infra', 'AI inference', 'People', 'Other']`, `FUNCTIONS = ['R&D', 'S&M', 'G&A', 'CS']` (§2, §3.2)
- `VENDOR_MASTER` and a headcount-by-function reference (§3.2)
- `ELASTICITY_BY_SEGMENT` and WTP mean/noise parameters for `willingness_to_pay_usd_per_seat` (§3.4)
- `ACCOUNT_SIZE_BAND_EDGES`, `DEAL_SIZE_BAND_EDGES`, `UTILISATION_BAND_EDGES` — the HTML's illustrative numeric edges (§2, §7 decision 5)
- `ADDON_CATALOG` — a real add-on product list (§1, Expansion + Monetisation)
- `ONBOARDING_STEPS_SELF_SERVE` and `ONBOARDING_STEPS_SALES_LED` — two lists, replacing the single `ONBOARDING_STEPS` (`config.py:221-227`), named per the HTML's step vocabulary (§1)
- A real Core/Power promotion rule (today `EVENTS_PER_MONTH`'s `'Core'`/`'Power'` keys, `config.py:236-237`, are unreferenced dead code — wiring them in is a config *and* `simulation.py` change) (§1)
- A second `PLAN_MASTER` SCD-2 price point on a different tier, so elasticity has more than one data point to be observed from (§3.4)

**Existing constants to rename/replace (values only, not structure):**
- `GEOS`: `'North America'`→`'NA'`, `'Europe'`→`'EMEA'` (§2)
- `INDUSTRIES`/`INDUSTRY_WEIGHTS`: replace the 10-value list with the HTML's 5 values + new weights (§2, §7 decision 1)
- `CHANNELS`/`CHANNEL_WEIGHTS`: replace with `['Paid', 'Organic', 'Referral', 'Direct']`, redistributing the weight currently held by `product_led`/`field_sales` (§2)
- Every dict keyed by `'Mid-Market'` — `SEGMENT_PLAN_DISTRIBUTION`, `ICP_EMPLOYEE_RANGE`, `ICP_REVENUE_RANGE`, `USERS_PER_ACCOUNT`, `DISCOUNT_BY_SEGMENT`, `CSM_BY_SEGMENT`, plus `ICP_SEGMENTS` itself — all need the key renamed to `'Mid-market'` consistently, or account generation will silently break on a lookup miss (§2)
- `ACCOUNT_MONTHLY_WEIGHTS`: 20 entries → 21, renormalized, continuing the existing taper (§4.1)
- `ONBOARDING_STEPS`: retired, replaced by the two motion-specific lists above

### `simulation.py`

**Module-level / existing functions to modify:**
- `MONTH_RANGE` (line 49) and `generate_plan()`'s `sim_end_month` (line 142): extend end bound to `'2026-09-01'` (§4.1)
- `generate_campaign()`: channel-value remap; add a `Referral` traffic path; restructure or supplement to emit weekly performance rows, not just one monthly-aggregated row (§4.2)
- `generate_account()`: add `motion`; rename region/segment/industry values; consume 21 weights; add `willingness_to_pay_usd_per_seat`
- `generate_cohort()` + `update_cohort()`: add a weekly-grain variant alongside monthly (§4.2)
- `generate_visitor()`: channel remap; add a real `qualify` flag/timestamp; wire in `Referral`-sourced visitors
- `generate_user()`: fork onboarding-step assignment by `motion`; add `value_moment_at`; implement real Core/Power promotion (currently dead)
- `generate_seat()`: propagate `motion`; add the seats-used vs. seats-purchased distinction needed for `Seat utilisation`
- `generate_contract()`: add discrete discount-grant/price-change/tier-change/add-on-attach event rows (today these are static fields set once, `simulation.py:556-640`); add `deal_size_band`; tag rows with `space`; consumes the new second SCD-2 price point
- `generate_expansion_opportunity()`: rename `motion_type` values to `Self-serve`/`Sales-led`; split `trigger_type` into discrete activity rows (`seat_add`/`tier_upgrade`/`add_on_buy`/`hit_limit`/`upsell_convo`) instead of one categorical field; add `seat_utilisation_pct` + band
- `generate_support_ticket()`: add a `QBR` ticket type/category
- `generate_health_score_snapshot()`: relabel `health_band` to `Green`/`Yellow`/`Red`; extend the week range to include September (`simulation.py:904`)
- `validate_all()`: `expected_months` 20→21 (§4.1)
- `main()`: wire every new `generate_*` call into the pipeline in dependency order, add each to the `dfs` dict, drop any new internal-only helper columns before save

**New functions to add:**
- `generate_mrr_movement()` — the bridge fact table (§3.3), the single highest-leverage addition
- `generate_cost_centre()`, `generate_vendor()`, `generate_headcount()` — Cost & Burn (§3.2)
- `generate_team()` — Expansion
- `generate_addon_catalog()`, `generate_discount_grant()`, `generate_price_change_event()` — Monetisation discrete activities (§1)
- `generate_revenue_line()` and `generate_cash()` — the two P&L raw-data gaps (§3.1). **No** `generate_pnl()` / `p_and_l` table — resolved as a pure query over Revenue engine + Cost & Burn + these two, never a stored result (§3.1)

### `schema/clickhouse_ddl.sql`
- New `CREATE TABLE` blocks for every new table listed above, mirroring whatever columns the matching `generate_*` function produces
- Since this file already follows DROP+CREATE (not ALTER, `clickhouse_ddl.sql:4`), adding new columns to existing tables (`account.motion`, `.willingness_to_pay_usd_per_seat`, `.account_size_band`, `.deal_size_band`, etc.) is just editing the existing `CREATE TABLE` column lists — no migration logic needed

### `load_to_clickhouse.py`
This file is **not generic** — it's driven entirely by four hardcoded dicts (`TABLE_ORDER`, `NULLABLE_COLS`, `BOOL_COLS`, `DATETIME_COLS`, lines 24-80), so every new/changed table needs a manual entry:
- `TABLE_ORDER`: append every new table name, in FK-safe order (e.g. `cost_centre`/`vendor` before anything that references them; `mrr_movement` after `account`/`contract`/`expansion_opportunity` since it's built from them)
- `NULLABLE_COLS`, `BOOL_COLS`, `DATETIME_COLS`: add an entry for every new nullable/boolean/datetime column on every new or changed table
- **No change needed to the actual logic** (`load_table()`, `coerce_df()`, `run_ddl()`) — this file's part of the work is pure data-entry into those four dicts, not new code paths

---

Ready to move to implementation once given the go-ahead.
