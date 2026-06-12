# Almacena BV — Contractor Allocation Review, Q1 2026

**Prepared:** 2026-05-17.
**Source:** Every PDF in `clients/almacena/raw/accounting/Almacena BV/01-03 EUR + USD Invoices/`. Holding BV contains only 2025 invoices — out of scope.
**FX:** USD → EUR at **1.087 USD per EUR** (per `config.yaml`; flagged in README as needing team sign-off).

---

## Why this exists

The accountant currently books **all** consulting and contractor invoices to a single G&A line — `Professional Services / Professional Services`. As of Q1 2026 actuals (consolidated):

| Line | Jan | Feb | Mar | **Q1 total** |
|---|---:|---:|---:|---:|
| G&A / Professional Services | 39,970 | 37,308 | 45,475 | **122,753** |
| R&D / Contractors | 463 | 256 | 92 | **811** |
| S&M / External Contractors | 0 | 0 | 0 | **0** |
| All payroll lines (R&D, S&M, G&A) | 0 | 0 | 0 | **0** |
| Production Payroll | 1,244 | 1,249 | 1,251 | **3,744** |

That €123k Prof Svc bucket is hiding R&D and S&M effort that should drive function-level OpEx ratios. This review identifies which invoices should move and where.

---

## Per-invoice table — Q1 2026, Almacena BV

Sorted by invoice month, then proposed bucket. Amounts shown in source currency; EUR-equivalents in the bucket summary.

### January 2026

| # | File | Vendor | Date | Amount | Cur | Description | Contractor? | **Proposed bucket** | Notes |
|---|---|---|---|---:|---|---|:---:|---|---|
| 1 | `Invoice Consulting Fee Iñigo January 2026.pdf` | Iñigo de Aresti Puyo | 2026-01-14 | 4,317.82 | EUR | Consulting services Jan 2026 | Y | **G&A / Prof Svc / Prof Svc** *(or R&D / S&M)* | Role unclear from invoice. **Needs client confirmation.** |
| 2 | `Invoice#1.pdf` | Mario David Linares Miranda | 2025-12-30 | 3,100.00 | USD | BDR Central America consulting (Dec 2025) | Y | **S&M / External Contractors** | Dec 2025 service period, paid Jan. |
| 3 | `December2025_expenses.pdf` | Mario David Linares Miranda | 2025-12 | 1,373.41 | USD | BDR CA travel expenses + equipment (Dec 2025) | Y | **S&M / External Contractors** *(or S&M / Travel)* | Dec 2025 service period. Includes one-off equipment purchase. |
| 4 | `Expenses trip CA_January 2026.pdf` | Mario David Linares Miranda | 2026-01 | n/a | USD | CA trip expenses Jan 2026 | Y | **S&M / Travel** | **Amount missing** — email summary only. Need original invoice. |
| 5 | `Invoice_AG00392025_Almacena_Dec 2025 BDM Consultant fee + Expenses.pdf` | Andres Gaviria | 2025-12-30 | 12,623.00 | USD | BDM Colombia: Dec fee $4,200 + bonus $8,400 + xfer $23 | Y | **S&M / External Contractors** | Dec 2025 service period. Bonus included — confirm bonus accounting. |
| 6 | `Invoice_AG00402026_Almacena_CA Expenses trip Jan 2026.pdf` | Andres Gaviria | 2026-01-26 | 3,832.00 | USD | CA expenses reimbursement Jan 2026 | Y | **S&M / Travel** | Pure expense reimbursement. |
| 7 | `001 - 26100029 - Almacena B.V. (200926).pdf` | Strik (law firm, NL) | 2026-01-02 | 1,815.00 | EUR | Monthly bookkeeping | N | **G&A / Prof Svc / Accounting** | Filed under USD March folder but EUR invoice. |
| 8 | `001 - 26100074 - Almacena B.V. (200926).pdf` | Strik (law firm, NL) | 2026-01-16 | 2,755.34 | EUR | Legal + tax + office support | N | **G&A / Prof Svc / Legal** | Same. |
| 9 | `Statement of Account_20260108135750668.pdf` | AON / AR Partnership | 2026-01-08 | 2,883.05 | EUR | Insurance claim — damaged container Arabica | N | **G&A / Prof Svc / Prof Svc** *(or Cost of Sales)* | Trade-related claim — possibly Cost of Service. Confirm. |
| 10 | `colppadsp3 - Original 1 of 1.pdf` | ING Bank Trade Finance | 2026-01-29 | 310.00 | EUR | Export collection fee (USD 182,457 collected) | N | **Cost of Sales / Cost of Service** | Transaction fee, not advisory. |
| 11 | `PHE-EXP-2526-357A.pdf` | Maersk | 2025-12-15 | 120.00 | USD | Uganda coffee export OBL amendment | N | **Cost of Sales / Cost of Service** | |
| 12 | `PHE-EXP-2526-377.pdf` | Maersk | 2026-01-05 | 2,450.00 | USD | Uganda → Dubai coffee shipment | N | **Cost of Sales / Cost of Service** | |
| 13 | `PHE-EXP-2526-421.pdf` | Maersk | 2026-01-28 | 1,500.00 | USD | Uganda → Mombasa Robusta shipment | N | **Cost of Sales / Cost of Service** | |
| 14 | `Almacena factura 4124527266.pdf` | Happy Mondays Guatemala | 2025-12-02 | 2,130.00 | USD | LATAM recruitment services | N | **G&A / Prof Svc / Prof Svc** *(or S&M)* | Recruiting BDRs — arguably S&M. Confirm. |
| 15 | `2026-1432.pdf` | Employes B.V. | 2026-01-01 | 48.34 | EUR | Salary/HR software (Dec 2025) | N | **G&A / IT & Software Subscriptions** | |
| 16 | `2026-48483.pdf` | Moneybird B.V. | 2026-01-18 | 47.19 | EUR | Accounting SaaS subscription | N | **G&A / IT & Software Subscriptions** | |
| 17 | `INV13320223_B01340177_01262026.pdf` | Box.com (UK) | 2026-01-26 | 13.50 | EUR | Box Starter licenses | N | **G&A / IT & Software Subscriptions** | |
| 18 | `AMSR003169686.pdf` | DHL Express | 2026-01-15 | 30.60 | EUR | Domestic courier | N | **G&A / Communication** | |
| 19 | `Abonnementsfactuur V04260021.pdf` | ParkingYou (Riekerpolder) | 2026-01-26 | 195.67 | EUR | Amsterdam parking subscription | N | **G&A / Rent & Utilities** | |
| 20 | `factuur_Januari 2026.pdf` | Vodafone Libertel | 2026-01-13 | 88.62 | EUR | Mobile telephony + device | N | **G&A / Communication** | |
| 21 | `Factuur 421002996809.pdf` | NS Reizigers | 2026-01-14 | 3.37 | EUR | OV-chipkaart (public transit) | N | **G&A / Travel** | |
| 22 | `Lucky Blessing VF25-100444.pdf` | Lucky Blessing (Shipping) | 2025-10-31 | 369.00 | EUR | Container handling (coffee) | N | **Cost of Sales / Cost of Service** | Oct 2025 — out of Q1 period. |
| 23 | `Almacena Mail - 20754 Booking summary.pdf` | B. Amsterdam | 2026-01-16 | n/a | EUR | Meeting room rental (2 hrs) | N | **G&A / Team Development** | **Amount missing** — booking email only. |
| 24 | `invoice almacena.pdf` | — | — | — | — | — | — | — | **Unreadable** — empty/corrupted PDF. |

### February 2026

| # | File | Vendor | Date | Amount | Cur | Description | Contractor? | **Proposed bucket** | Notes |
|---|---|---|---|---:|---|---|:---:|---|---|
| 25 | `MB290324MS.pdf` | Nua Holding BV (D. Yanchev PSC) | 2026-02-11 | 7,917.00 | EUR | "MS" — Mgmt Services Jan 2026 | Y? | **R&D / Contractors** *(or G&A / Prof Svc)* | **Largest single recurring contractor.** Founder/exec PSC. **Bucket depends entirely on role** — CTO/Tech → R&D; CEO/general mgmt → G&A. Get client confirmation before booking. |
| 26 | `MB290325MS.pdf` | Nua Holding BV (D. Yanchev PSC) | 2026-02-28 | 7,917.00 | EUR | "MS" Feb 2026 | Y? | **R&D / Contractors** *(or G&A / Prof Svc)* | Same as above. |
| 27 | `001 - 26100161 - Almacena B.V. (200926).pdf` | Strik | 2026-02-05 | 6,849.79 | EUR | Legal + bookkeeping + tax + office | N | **G&A / Prof Svc / Legal** | |
| 28 | `001 - 26100195 - Almacena B.V. (200926).pdf` | Strik | 2026-02-09 | 1,815.00 | EUR | Monthly bookkeeping | N | **G&A / Prof Svc / Accounting** | |
| 29 | `January 2026 Expenses.pdf` (Mario) | Mario Linares | 2026-01-30 | 3,398.94 | USD | BDR Jan consulting $3,100 + branded merch $247 + xfer | Y | **S&M / External Contractors** | Filed in Feb folder. Merch portion arguably S&M / Direct Marketing. |
| 30 | `February2026.pdf` (Mario) | Mario Linares | 2026-02-27 | 3,157.18 | USD | BDR Feb consulting $3,100 + internet $57 | Y | **S&M / External Contractors** | |
| 31 | `Invoice BDR Yeny Rey Colombia-January 2026.pdf` | Yeny Rey | 2026-02-02 | 1,000.00 | USD | BDR Colombia Jan | Y | **S&M / External Contractors** | |
| 32 | `Invoice BDR Yeny Rey Colombia-February 2026.pdf` | Yeny Rey | 2026-02-03 | 1,000.00 | USD | BDR Colombia Feb | Y | **S&M / External Contractors** | |
| 33 | `Invoice_AG00412026_Almacena_BDM Colombia_FEB 2026.pdf` | Andres Gaviria | 2026-02-12 | 4,223.00 | USD | BDM Feb expenses + xfer | Y? | **S&M / External Contractors** *(or S&M / Travel)* | Looks expense-heavy; need itemization to confirm fee vs reimbursement split. |
| 34 | `Lorna A January 2026 invoice and allowances.pdf` | Imelda Lorna Amongi | 2026-02-09 | 1,179.72 | USD | Consulting + comms + facilitation + DHL (Jan) | Y | **S&M / External Contractors** *(or Cost of Sales / Production)* | Uganda-based. "Facilitation/DHL" hints at on-the-ground origination support — could be ops/origination, not S&M. **Needs client confirmation.** |
| 35 | `PHE-EXP-2526-473.pdf` | Phenix Freighters | 2026-02-19 | 3,455.00 | USD | Uganda → Spain coffee shipment + storage | N | **Cost of Sales / Cost of Service** | Filed under EUR folder but USD invoice. |
| 36 | `inv172502882.pdf` | B.1. B.V. | 2026-02-11 | 343.74 | EUR | Fixed desk workspace | N | **G&A / Rent & Utilities** | |
| 37 | `Abonnementsfactuur V04260082.pdf` | ParkingYou | 2026-02-25 | 195.67 | EUR | Parking subscription | N | **G&A / Rent & Utilities** | |
| 38 | `factuur_Februari 2026.pdf` | Vodafone | 2026-02-15 | 70.05 | EUR | Mobile | N | **G&A / Communication** | |
| 39 | `2026-132829.pdf` | Moneybird | 2026-02-18 | 47.19 | EUR | Accounting SaaS | N | **G&A / IT & Software Subscriptions** | |
| 40 | `2026-6317.pdf` | Employes | 2026-02-01 | 48.34 | EUR | HR/payroll SaaS | N | **G&A / IT & Software Subscriptions** | |
| 41–47 | `2026-T-0123.pdf`, `EX-26-0046/47/48/49.pdf`, `UG2600266/267.pdf` | — | — | — | — | — | — | — | **Unreadable — scans without OCR.** 7 PDFs in Feb USD folder. Filename prefixes (EX = expenses, UG = Uganda) suggest more LATAM/Uganda contractor expense claims. **Need re-scan with text layer or manual entry.** |

### March 2026

| # | File | Vendor | Date | Amount | Cur | Description | Contractor? | **Proposed bucket** | Notes |
|---|---|---|---|---:|---|---|:---:|---|---|
| 48 | `Invoice Consulting Fee Iñigo March 2026.pdf` | Iñigo de Aresti Puyo | 2026-03-30 | 1,799.09 | EUR | Consulting Mar 2026 | Y | **G&A / Prof Svc / Prof Svc** *(or R&D / S&M)* | Same person as #1. Lower amount (part-month?). Feb invoice missing. |
| 49 | `MB290326MS.pdf` | Nua Holding BV | 2026-03-06 | 9,579.57 | EUR | "MS" Mar 2026 | Y? | **R&D / Contractors** *(or G&A / Prof Svc)* | Rate increased from €7,917 → €9,580 starting March. Confirm change. |
| 50 | `MB290327MS.pdf` | Nua Holding BV | 2026-03-26 | 9,579.57 | EUR | "MS" April 2026 (prepaid) | Y? | **R&D / Contractors** *(or G&A / Prof Svc)* | **Prepayment for April** — accrual question: book to March or April? |
| 51 | `faktura-0000000308-25.03.2026-Almacena_BV.pdf` | Rayters Blok ООД (Sofia) | 2026-03-25 | 1,800.00 | EUR | Company website creation, 50% advance | Y | **R&D / Contractors** | Bulgarian web dev vendor. Capex vs opex? If site is a marketing asset, could argue **S&M / Direct Marketing**. |
| 52 | `001 - 26100214 - Almacena B.V. (200926).pdf` | Strik | 2026-03-05 | 10,415.24 | EUR | Legal + bookkeeping + tax + travel | N | **G&A / Prof Svc / Legal** | Largest Strik invoice — includes travel. |
| 53 | `001 - 26100262 - Almacena B.V. (200926).pdf` | Strik | 2026-03-05 | 1,815.00 | EUR | Monthly bookkeeping | N | **G&A / Prof Svc / Accounting** | |
| 54 | `Invoice_AG00422026_Almacena_BDM Colombia_March 2026-2.pdf` | Andres Gaviria | 2026-03-02 | 4,245.00 | USD | BDM March expenses + xfer | Y | **S&M / External Contractors** | |
| 55 | `Expenses March_2026 LATAM.pdf` | Mario Linares | 2026-03-31 | 4,224.88 | USD | BDR Mar consulting + travel + meals | Y | **S&M / External Contractors** | Mixed fee + expense — confirm split. |
| 56 | `Lorna A February 2026 invoice and allowances.pdf` | Imelda Lorna Amongi | 2026-03-10 | 1,179.72 | USD | Consulting + comms (Feb) | Y | **S&M / External Contractors** *(or Cost of Sales / Production)* | **Same file as #34** — appears in both Feb USD and Mar USD folders. Count once. |
| 57 | `PHE-EXP-2526-514.pdf` | Phenix Freighters | 2026-03-23 | 1,920.00 | USD | Kampala → Kenya/Russia coffee export | N | **Cost of Sales / Infrastructure** *(or Cost of Service)* | |
| 58 | `2026-11094.pdf` | Shine Employes B.V. | 2026-03-01 | 48.34 | EUR | HR/payroll SaaS | N | **G&A / IT & Software Subscriptions** | |
| 59 | `AMSR003271431.pdf` | DHL Express | 2026-03-30 | 30.60 | EUR | Courier | N | **G&A / Communication** | |
| 60 | `Abonnementsfactuur V04260139.pdf` | ParkingYou | 2026-03-24 | 195.67 | EUR | Parking | N | **G&A / Rent & Utilities** | |
| 61 | `INV13460062_B01340177_03262026.pdf` | Box.com | 2026-03-26 | 13.50 | EUR | Box licenses | N | **G&A / IT & Software Subscriptions** | |
| 62 | `factuur_Maart 2026.pdf` | Vodafone | 2026-03-14 | 48.62 | EUR | Mobile | N | **G&A / Communication** | |

---

## Roll-up by proposed bucket (Q1 2026, BV-only, EUR equivalents)

USD converted at 1.087 USD/EUR. Dec-2025-dated invoices paid in Jan included where they appear in Q1 folders. Lorna #56 (duplicate of #34) excluded.

### Contractor invoices that should leave "Professional Services"

| Proposed bucket | Vendor | Q1 EUR equiv | Notes |
|---|---|---:|---|
| **R&D / Contractors** | Nua Holding BV (D. Yanchev) | 25,414 | Conditional on confirming Dimo's role as tech/CTO. Mar incl. April prepayment €9,580 — accrual decision pending. |
| **R&D / Contractors** | Rayters Blok (web dev) | 1,800 | Or S&M if site is marketing-led. |
| **R&D / Contractors subtotal** | | **27,214** | |
| **S&M / External Contractors** | Andres Gaviria (BDM Colombia) | 22,927 | Includes Dec 2025 service (€11,612 paid Jan). Bonus accounting to confirm. |
| **S&M / External Contractors** | Mario Linares (BDR Central America) | 13,113 | Q1 invoices €9,917 + Dec 2025 service paid Jan €4,116. Excludes the Jan trip expenses invoice with missing amount (#4). |
| **S&M / External Contractors** | Yeny Rey (BDR Colombia) | 1,840 | |
| **S&M / External Contractors** | Imelda Lorna Amongi (Uganda) | 2,171 | **Could instead be Cost of Sales / Production** if she does origination/ops, not sales. |
| **S&M / External Contractors subtotal** | | **40,051** | |
| **Total leaving Prof Svc → R&D + S&M** | | **~67,265** | |

### Genuinely "Professional Services" (no change proposed)

| Bucket | Vendor | Q1 EUR | Notes |
|---|---|---:|---|
| G&A / Prof Svc / Legal | Strik (legal portions) | ~20,020 | Inv #8, #27, #52 — legal + tax + office support. |
| G&A / Prof Svc / Accounting | Strik (monthly reporting) | 5,445 | Inv #7, #28, #53 — 3 × €1,815. |
| G&A / Prof Svc / Prof Svc | Iñigo de Aresti Puyo | 6,117 | **Could be R&D or S&M** — needs role confirmation. |
| G&A / Prof Svc / Prof Svc | AON insurance claim | 2,883 | Or Cost of Sales (trade-related). |
| G&A / Prof Svc / Prof Svc | Happy Mondays Guatemala (HR recruitment) | 1,960 | Or S&M (recruiting sales hires). |
| **Subtotal** | | **~36,425** | |

### Not contractors — likely already in correct buckets

| Bucket | Q1 EUR | What |
|---|---:|---|
| Cost of Sales / Cost of Service | ~7,750 | Maersk + Phenix freight, ING export collection, Lucky Blessing (Oct 2025) |
| G&A / IT & Software Subscriptions | 282 | Employes ×3 + Moneybird ×2 + Box ×3 |
| G&A / Communication | 268 | Vodafone ×3 + DHL ×2 |
| G&A / Rent & Utilities | 931 | ParkingYou ×3 + B.1. workspace |
| G&A / Travel | 3 | NS Reizigers |
| G&A / Team Development | n/a | B. Amsterdam meeting room (amount missing) |
| **Subtotal** | **~9,234** | |

---

## What this means for the deck

Current Q1 2026 consolidated actuals show **€122,753 in G&A / Professional Services**. This review identifies **~€67k** of BV invoices that should reallocate away from Prof Svc:

- → **R&D / Contractors:** ~€27k (currently shows €811 Q1)
- → **S&M / External Contractors:** ~€40k (currently shows €0 Q1)

That's roughly a **55% reduction** in the Prof Svc line for BV, with the remaining ~€36k correctly belonging to Prof Svc (Legal, Accounting, genuine advisory).

**Gap to explain.** The BV invoices I could read sum to ~€113k. The €123k consolidated figure likely also includes:
- ap_foundation entity invoices not in this BV folder review
- The 8 unreadable Feb USD PDFs (likely more LATAM/Uganda contractors)
- Other Strik/legal items not in the period folders

---

## Questions to settle with client + accountant

1. **Nua Holding BV / Dimo Yanchev role.** What function — CTO/Product (→ R&D), CEO/general mgmt (→ G&A), or split? This is the single largest contractor (~€25k Q1 BV, recurring monthly, rate stepped up in March from €7,917 → €9,580 — confirm).
2. **Iñigo de Aresti Puyo's role.** Sales? Product? Advisory?
3. **Imelda Lorna Amongi's role.** S&M (sales/BDR) or Cost of Sales / Production (origination, KYC, ops)?
4. **Andres Gaviria's December bonus** ($8,400) — opex period? Cash vs accrual?
5. **Andres Gaviria Feb invoice ($4,223)** — itemize fee vs expenses for clean split between External Contractors and S&M / Travel.
6. **Mario Linares' embedded expenses** (equipment $247 Dec, branded merch Jan, internet Feb) — pull out of consulting fee line?
7. **Rayters Blok website** — R&D (engineering asset) or S&M (marketing site)? Capex consideration?
8. **AON insurance claim & ING trade-finance fee** — Cost of Service rather than Prof Svc?
9. **Happy Mondays Guatemala recruitment** — booking BDR recruiting costs to G&A or S&M?
10. **8 unreadable Feb USD PDFs** (`EX-26-00xx`, `UG260026x`, `2026-T-0123`) — need re-scan with text layer or manual data entry. Filenames suggest LATAM expense claims + Uganda invoices.
11. **`Expenses trip CA_January 2026.pdf`** (Mario) and **`Almacena Mail booking summary`** — amounts not captured; need underlying invoice.
12. **Holding BV Q1 2026 invoices** — none present in `raw/accounting/Almacena Holding BV/`. Are there any? If yes, request them.
13. **Reclassify retroactively or starting next period?** If retro, scope and re-run will need agreement (changes Q1 deck numbers).
