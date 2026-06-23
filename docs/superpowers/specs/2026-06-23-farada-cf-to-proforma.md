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
