# Spec — move the CF engine into the ProForma; make statements pure output (Cupffee parity)

Per the model-building skill (pillar 2/3): **the ProForma is the calc engine; IS/CF/BS are thin —
pull from the ProForma and present.** Farada violates this for the **cash flow**: the direct-method
derivation (`cash from customers = Rev − ΔAR`, cash-as-plug roll) lives *in the CF statement*
(`build_cf`), and the ProForma's CASH FLOW / WC-ratios / TAXATION / FUNDING sections are **blank
placeholders**. Replicate Cupffee — move the CF derivation into the ProForma, fill the WC ratios, and
thin the CF statement to pure `=ProForma!` pulls.

## Reference: how Cupffee does it
`Pro Forma` carries the whole engine — INCOME STATEMENT · **BALANCE SHEET** (asset rolls, inventory,
VAT, deferred) · **WORKING CAPITAL DRIVERS & RATIO** (receivables/payables) · **CASH FLOW** (cash
inflow/clients, cash outflow materials/suppliers, payments to personnel, CAPEX) · TAXATION · FUNDING.
The `CF` statement pulls each line (`=Pro Forma!…`) and only **sums the activity subtotals**
(`Net CF Operating = ΣΣ pulled lines`). Same for `BS`. The derivation is never in the statement.

## Farada current vs target
| Layer | Today | Target |
|---|---|---|
| ProForma BALANCE SHEET rolls (AR/AP/deferred/PP&E/SC/debt/RE) | ✓ populated (124–136) | unchanged |
| ProForma **CASH FLOW** (145–148) | **blank headers** | **full direct-method derivation + cash roll** |
| ProForma **WC DRIVERS & RATIOS** (138–143) | **blank** | DSO/DPO realised + current/quick/cash ratios |
| ProForma TAXATION / FUNDING (150–157) | blank | thin refs to IS tax / financing-roll movements |
| **CF statement** (`build_cf`) | **holds the derivation** (`Rev−ΔAR`, cash plug) | **pure `=ProForma!` pulls** |
| BS statement | pulls rolls; cash `=CF!ending` | cash `=ProForma!<ending cash>`; rolls unchanged |

## Architecture decisions
- **ProForma computes EVERYTHING for the CF** — each line derivation, the operating/investing/
  financing subtotals, and the beginning/excess/ending **cash-as-plug roll**. The CF statement becomes
  **100% `=ProForma!` references** (no sums in the statement). This is the strict reading of the user's
  "statements are pure output, not a calc sheet" — stricter than Cupffee (which sums subtotals in the
  statement) and the skill (which permits statement subtotals). *(Confirm — see open Q2.)*
- **Append, don't insert.** The lower ProForma sections are append-only (rows 124+; nothing references
  below them yet), so expanding CASH FLOW/WC/TAX/FUNDING with real rows needs **no ref remap** of the
  existing engine. The statements (built after) reference the new rows.
- **The CF derivation is unchanged in logic** — it's the exact direct method already in `build_cf`
  (`cash from customers = Rev − ΔAR`; `cash to suppliers = −(COGS+OpEx−payroll) + ΔAP`; personnel;
  taxes; bank charges; Δdeferred; capex; equity/debt/grants; cash plug). We **relocate** it, not
  redesign it — so the balance oracle still holds by construction.

## Implementation insight — relocate by translation, not re-derivation
The correct, post-reflow CF derivation **already exists** in the CF statement (`build_cf` →
reflow-remapped → `restructure_cf`). So CB1 doesn't re-derive: it **translates** each CF-statement
formula into a ProForma CASH FLOW row — rewrite `ProForma!X{r}` → bare `X{r}` (internal) and the
intra-statement `CF!X{r}` (the cash roll) → the new ProForma CF rows. CB2 then overwrites each CF
statement cell with `=ProForma!{cfrow}`. Sections are **append-only** (`PF_SECTIONS`), so expanding
the CASH FLOW/WC/TAX/FUNDING line lists adds rows at the bottom with **no remap**. Build order:
populate the ProForma sections after `restructure_cf` finalises the derivation, then re-thin the
statement.

## Dependency graph
```
ProForma BS rolls (exist) ─┬─→ ProForma CASH FLOW derivation (CB1) ─→ ProForma cash roll
                           ├─→ ProForma WC ratios (CB3)
IS (tax, NP)  ─────────────┘
                                   │
              CF statement thin pulls (CB2) ─→ BS cash = ProForma ending (CB2)
                                   │
                           CF_Y / yearly mirror (restructure_cf) — still sums CF columns
```

## Tasks (vertical slices)
- [ ] **CB1 — CF derivation in the ProForma.** Expand the CASH FLOW section (145+) with the full
  direct-method line set + operating/investing/financing subtotals + beginning/excess/ending cash
  roll, referencing the BS rolls + IS. (Append rows; lay styles from the design system.)
  *Verify:* every CF line present & formula'd in ProForma; no `#REF!`; balance oracle still 0.
- [ ] **CB2 — thin the CF statement + repoint BS cash.** Rewrite `build_cf` so each CF line =
  `=ProForma!<row>` (pure output, incl. subtotals); BS cash `=ProForma!<ending cash>` (not `=CF!`).
  *Verify:* CF statement cells are all bare `=ProForma!` refs (no arithmetic); BS check=0; CF_Y mirror
  still sums correctly.
- [ ] **CB3 — WC drivers & ratios in the ProForma.** Populate DSO/DPO (realised) + current/quick/cash
  ratios (from BS components); BS ratio rows pull from them. *Verify:* ratios formula'd; BS ratio rows
  reference ProForma; sane magnitudes.
- [ ] **CB4 — TAXATION + FUNDING sections (thin refs).** Tax expense (P&L)→IS tax; tax payable→roll;
  equity/debt/grants→financing-roll movements. *Verify:* sections populated; no `#REF!`.
- [ ] **CB5 — verify + regenerate.** Balance oracle BS check=0, schema broken=0, full pytest,
  `model_logic.md` regenerated; eyeball CF ties (operating+investing+financing = Δcash).

### Checkpoint — after CB2 (the core ask) and again after CB5
ProForma is the CF engine; the CF statement is pure output; model still balances.

### ✅ CB1–CB4 SHIPPED (2026-06-23) — review checkpoint
- CB1/CB2 (c480b19): CF derivation + cash roll cloned into the ProForma CASH FLOW section (Δ-offset
  ref translation); CF statement is now 100% bare `=ProForma!` refs; BS cash → ProForma cash roll.
- CB3 (9269986): WC DRIVERS & RATIOS (DSO/DPO + current/quick/cash) computed in the ProForma; BS pulls.
- CB4 (681d8ee): TAXATION + FUNDING sections populated (thin refs to IS tax / rolls / financing).
- ProForma now carries the full skill-outline engine: BALANCE SHEET rolls (124) · WC DRIVERS & RATIOS
  (138) · CASH FLOW (145) · TAXATION (179) · FUNDING (183). Statements thin.
- Gates: balance oracle BS check=0 · schema broken-ref=0 · no `#REF!` · 392 pytest · CF_Y/BS_Y intact.
- **Relocation, not redesign** → values identical to pre-CB v7 by construction. CB5 (regenerate
  `model_logic.md`) + v8 promotion pending user review.

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Relocating CF changes a value / breaks the cash plug | High | logic is identical (relocation, not redesign); balance oracle + value eyeball vs current v7 |
| Statement-references break the CF_Y yearly mirror | Med | CF_Y sums CF columns; thin pulls preserve column values — verify CF_Y unchanged |
| Big append shifts statement refs to ProForma | Low | lower sections are append-only; statements built after, reference final rows |
| Two cash-roll definitions drift (ProForma vs old statement) | Med | delete the statement-side derivation entirely in CB2; single source in ProForma |

## DECISIONS (2026-06-23, confirmed)
1. **Full parity** — CB1–CB4 (CF engine→ProForma + thin statement + WC ratios + TAXATION + FUNDING).
2. **ProForma computes the CF subtotals + cash roll** — the CF statement is 100% bare `=ProForma!`
   references (zero arithmetic).
3. **Keep v7 in place** (edit the one builder; promote to v8 later).

## ⚠️ REVISED (2026-06-23) — corrected intent; supersedes CB1/CB2/CB4
User feedback: *"that's not what I meant on the cash flow; taxation looks wrong; just copy the Cupffee
template; ignore the 100%-draw-from-ProForma ask."* CB1 wrongly **cloned Farada's lumped one-line CF
derivation**; the ask is to rebuild the ProForma CASH FLOW + TAXATION to **Cupffee's actual template**,
and let the statements **pull lines + sum subtotals** (Cupffee-style), not be 100% bare refs. CB3 (WC
ratios) stands. Build **forward** (replace `relocate_cf_to_proforma`), don't git-revert.

### Cupffee CASH FLOW template (Farada-adapted) — cash by component
Each line = accrual ± Δ(working-capital balance). Farada's per-category AP buckets (COGS 126 / S&M 127
/ G&A 128 / R&D 129) + payroll payable (131) + AR (125) + deferred (132) make this map 1:1:
- **Cash inflow / clients** = `Rev(28) − ΔAR(125)`  ·  **Movement in deferred revenue** = `Δdeferred(132)`
- **Cash outflow — Suppliers** (split, each `−(cost − ΔAP_cat)`):
  Direct/COGS `−(53 − ΔAP126)` · S&M `−((74−75) − ΔAP127)` · G&A `−((83−84) − ΔAP128)` · R&D `−((94−95) − ΔAP129)`
- **Payments to personnel** = sub-lines S&M(75)/G&A(84)/R&D(95) gross; subtotal nets `Δpayroll-payable(131)`
- **Corporate & other taxes** = `IS tax(108) + Δtax-payable(133)`
- **Investing**: CAPEX `−119` · R&D capitalised `0`
- **Financing**: Equity `ΔSC(134)` · Debt `ΔDebt(135)` · Grants `103`
- **Cash roll**: Beginning(t0=OB / prior ending) · Excess(=Op+Inv+Fin) · Ending
*(Farada is fabless → no "Cash outflow Materials" / inventory line.)*

### Cupffee TAXATION template (tax-loss carryforward) — the "looks wrong" fix
Farada currently does `tax = −MAX(0,PBT)×rate` with **no NOL carryforward** → overstates tax in the
catch-up years. Replicate Cupffee:
- Taxable profit before utilisation = `IS PBT(107)`
- Utilisation of tax loss = `−MIN(opening_loss_balance, MAX(PBT,0))`
- Taxable profit after = before + utilisation
- **Total taxation** = `MAX(after × rate, 0)`
- **Tax-loss control account**: opening = prior closing · additions = `−MIN(PBT,0)` · utilisation (above) · closing = Σ
- **Corporate tax** = `−Total taxation`
- **IS "Income tax (expense)" (108) now references ProForma `−Total taxation`** (was the inline MAX).
  → changes NP / RE / cash (intended; more correct). The **balance oracle's synthetic tax must adopt
  the carryforward** to stay a valid check.

### Statements (revert the 100% rule)
CF/BS statements **pull the line items from the ProForma and sum the subtotals in the statement**
(Cupffee-style). Undo CB2's bare-ref-everything; keep line refs = `=ProForma!…`, subtotals = `SUM(...)`.

### Revised tasks (supersede CB1/CB2/CB4)
- [ ] **RB1 — ProForma CASH FLOW = Cupffee by-component** (replace the clone). Inflow/clients + deferred;
  Suppliers split by COGS/S&M/G&A/R&D (cost − ΔAP_cat); personnel by category; taxes; CAPEX; financing;
  cash roll. *Verify:* lines present & itemised; operating total reconciles to the prior lumped total
  (value-neutral except tax); balance oracle 0; no #REF!.
- [ ] **RB2 — TAXATION tax-loss carryforward** + IS tax → `−Total taxation`; update the balance oracle's
  synthetic tax to the carryforward. *Verify:* control-account rolls (opening/additions/utilisation/
  closing); tax=0 while cumulative losses exceed profit; BS check=0; oracle green.
- [ ] **RB3 — statements pull+sum** (revert pure-output). CF statement lines = `=ProForma!`, subtotals
  summed in-statement; BS unchanged. *Verify:* CF subtotals are `SUM` in the statement; CF_Y intact.
- [ ] **RB4 — verify + regenerate** `model_logic.md`; eyeball tax-loss schedule + CF ties.

### ✅ RB1–RB2 SHIPPED (supersede CB1/CB2/CB4)
- RB1 (61e74f1): ProForma CASH FLOW rebuilt to Cupffee by-component (inflow/clients; Suppliers split
  COGS/S&M/G&A/R&D as `−(cost − ΔAP_cat)`; Personnel by category + Movement in payroll payable; taxes;
  bank; CAPEX; financing; cash roll). **Value-neutral** decomposition. CF statement = pull lines +
  **sum subtotals** (Cupffee-style); BS cash = `=CF!` ending.
- RB2 (d8653b6): TAXATION = **tax-loss carryforward** (control account opening/additions/utilisation/
  closing → Total taxation → Corporate tax); IS income tax pulls the ProForma corporate tax. Balance
  oracle's synthetic tax updated to the carryforward; BS check=0 holds. Decisions: carryforward adopted;
  personnel gross-by-category, net Δ on subtotal.
- Gates: balance oracle 0 · schema broken-ref=0 · no #REF! · 392 pytest.
- Remaining: regenerate `model_logic.md` + eyeball the tax-loss schedule & CF ties in Excel; v8 later.

## Open questions (revised)
1. **Tax-loss carryforward changes the numbers** (lower tax through the loss-utilisation years) — confirm
   adopt now (you flagged taxation as wrong, so presumably yes).
2. **Personnel cash** — Farada has ONE payroll-payable roll (not per-category like Cupffee). OK to show
   gross personnel by S&M/G&A/R&D but net the single payroll-payable Δ on the subtotal?
