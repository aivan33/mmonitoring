# `build_rolling_budget.py` — v3 rewrite audit (Task 2.1)

Audit of the 2191-line v2.1.1 generator for the v3 indirect-derived rewrite.
**Headline:** the rewrite is smaller than feared. The indirect-CF math and the
cash-as-plug wiring **already exist** (built in v2.1 as a tie-out). v3 mostly
*promotes* them and *deletes* the direct-method scaffolding.

## Two facts that shrink Phase 3

1. **Cash-as-plug is already wired.** `build_pro_forma` emits
   `BS_CASH = =E{CLOSE_CASH}` (forecast cols) and `CLOSE_CASH = OPEN_CASH + NET_CHG_CASH`.
   The BS already reads cash from the CF. No change needed to the plug mechanic.
2. **The indirect CF already exists** as the `R.TIE_NI … R.TIE_NET_CHG` block
   (rows 179–205): Net income + D&A + non-cash + ΔWC (ΔAR/ΔInv/ΔAP/ΔPayPay/ΔTax/ΔVAT)
   + investing (ΔCAPEX ×3) + financing (equity/loan/grant/div). It was built to
   *validate* the direct method (`CF_TIE = NET_CHG_CASH − TIE_NET_CHG`). In v3 it
   becomes the **primary, visible** CF; `NET_CHG_CASH` points at it; the direct
   lines and `CF_TIE` are deleted.

So v3 = repoint `NET_CHG_CASH` at the indirect sum, relabel the `TIE_*` block as
the CF statement, delete the direct-method rows, add a *check-vs-actual-cash* row
for past columns. The cash plug and the indirect arithmetic carry over intact.

## Top-level symbol map

| Line | Symbol | Verdict | Notes |
|---|---|---|---|
| 89 | `class R` (row registry) | **REWRITE** | Reorder to BS → P&L → indirect CF. Delete direct-CF rows (`CASH_IN_*`, `CASH_OUT_*`, `CASH_OUT_DIRECT`, `CF_TIE`) and the direct-method helper rolls (`AR_HLP_*`, `AP_HLP_*`, `VAT_HLP_*`, `PURCHASES_DRV`, `INV_OUT_DRV`). Relabel `TIE_*` rows as the CF statement lines. Keep BS/IS leaf rows. Net: ~264 row consts → ~180. |
| 430 | `_load_actuals_from_db` | **KEEP** | Loads IS+BS (and CF) actuals + period flags from DB. v3 consumes IS+BS only; CF map entries become dead but harmless (or trim). |
| 504 | `fill_right` | **KEEP** | Core formula fill (Translator). Unchanged. |
| 525 | `fy_sum` / 529 `fy_last` | **KEEP** | FY-total column helpers. Unchanged. |
| 533 | `label` | **KEEP** | Row labelling/styling. Unchanged. |
| 555 | `class I` (Inputs registry) | **KEEP (minor)** | Inputs row map. Keep; trim any direct-method-only driver rows if unused. |
| 661 | `faradaox_monthly_qty` | **KEEP** | Revenue driver helper. Unchanged. |
| 678 | `build_inputs` | **KEEP (minor)** | Inputs sheet builder. Verify seeded from `realistic` (Task 1.2); likely unchanged. |
| 960 | `clean_inputs_labels` | **KEEP** | Cosmetic. Unchanged. |
| 989 | `inp_abs` / 993 `inp_period` / 997 `_prev_col` | **KEEP** | Cell-ref helpers. Unchanged. |
| 1005 | `build_pro_forma` (~895 LOC) | **REWRITE (the bulk)** | BS section: keep carry-forward + cash-as-plug (already correct). IS: keep. CF: delete direct lines (≈ lines 563–650), promote indirect block to the visible CF, repoint `NET_CHG_CASH`, drop `CF_TIE`, add check-vs-actual-cash row. Remove direct-method helper-roll emission (AR/AP/VAT/purchases). |
| 1900 | `apply_source_styling` | **KEEP** | Styling pass. Unchanged. |
| 1991 | `setup_outline_groups` | **KEEP (adjust)** | Outline groups for helper rows — update row refs to the new layout. |
| 2045 | `build_actuals` | **KEEP** | Builds Actuals sheet from DB. Now sources restated Jan–Apr (Task 0.1). Unchanged logic. |
| 2110 | `main` | **KEEP (minor)** | Orchestration + self-check. Update any hardcoded row refs. |

## LOC estimate

| Zone | LOC | Action |
|---|---|---|
| Safe core (loaders, helpers, styling, inputs, actuals) | ~1,000 | KEEP as-is |
| `class R` registry | ~340 | REWRITE (reorder, prune ~80 rows) |
| `build_pro_forma` CF section | ~150 (of 895) | REWRITE (promote indirect, delete direct) |
| `build_pro_forma` BS/IS sections | ~745 | MOSTLY KEEP (BS cash-plug already right; verify) |
| Direct-method helper-roll emission + `CF_TIE` | ~90 | DELETE |

Net new/changed: **~400–500 LOC** touched, concentrated in `class R` and the CF
portion of `build_pro_forma`. The rest is keep/verify.

## Risks flagged

- **Past-column CF + check-vs-actual-cash:** in actual months, BS lines (incl. cash)
  pull from Actuals; the derived CF's `CLOSE_CASH` must be compared (not equated) to
  the pulled actual cash → add a `CASH_CHECK` row, do **not** force `BS_CASH = CLOSE_CASH`
  in past columns (only in forecast). This is the one genuinely new wiring.
- **Indirect block completeness:** every non-cash BS leaf delta must appear in the CF.
  The existing `TIE_*` block covers AR/Inv/AP/PayPay/Tax/VAT + CAPEX×3 + equity/loan/grant/div.
  Confirm no BS leaf added since (e.g. Prepaid, Loans-neg, Other-recv) is missing a ΔWC line.
- **`freeze_and_validate.py`** already noted obsolete (v2.1 plan) — untouched.
