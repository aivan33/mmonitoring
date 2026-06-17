"""Print the 'new this month' candidate invoices for human review before they
are appended to the MRR Schedule's Source Data.

Selection is a manual judgment in practice, so this list is generous + flagged:
  TYPO  - raw invoice date was implausible (e.g. 3036); corrected via Start year
  DUP?  - client+product+amount matches an earlier invoice (possible renewal)
  CREDIT- negative amount (reversal / credit note)

Usage: python clients/unde/one_offs/list_candidates.py <YYYY-MM> [categorization.xlsx]
Defaults to the May 2026 Categorization. FX = ECB monthly averages.
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mrr_source_data import candidates, to_source_row

C = Path(__file__).resolve().parents[1] / "raw"
# ECB monthly-average FX (RON/EUR, USD/EUR) per reporting month.
FX = {"2026-05": (5.229615, 1.1673), "2026-04": (5.0991, 1.1706)}


def s(x):
    return "" if x is None else (
        x.strftime("%Y-%m-%d") if isinstance(x, dt.datetime) else str(x))


def main():
    period = sys.argv[1] if len(sys.argv) > 1 else "2026-05"
    year, month = int(period[:4]), int(period[5:7])
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        C / "Undelucram Categorization May 2026.xlsx"
    fx_ron, fx_usd = FX.get(period, (5.229615, 1.1673))

    cand = candidates(path, year, month)
    rows = [(c, to_source_row(c, fx_ron, fx_usd)) for c in cand]
    print(f"{period} candidates: {len(cand)}  (FX RON {fx_ron}, USD {fx_usd})\n")
    hdr = f"{'#':>2} {'cur':3} {'amount':>10} {'Val€':>6} {'client':16} " \
          f"{'country':8} {'produs':16} {'P':>2} {'MRR':3} {'Start':10} flags"
    print(hdr)
    tot = 0.0
    for i, (inv, sr) in enumerate(sorted(rows, key=lambda x: x[0]["_eff_date"]), 1):
        flags = []
        if inv["_date_typo"]:
            flags.append(f"TYPO(raw {s(inv['date'])})")
        if inv["_dup_of_count"] > 0:
            flags.append(f"DUP?x{inv['_dup_of_count']}")
        if isinstance(sr["amount"], (int, float)) and sr["amount"] < 0:
            flags.append("CREDIT")
        mrr = s(sr["mrr"])
        if mrr.upper() == "MRR" and isinstance(sr["monthly"], (int, float)):
            tot += sr["monthly"]
        print(f"{i:>2} {s(sr['currency'])[:3]:3} {sr['amount']:>10.2f} "
              f"{sr['valoare']:>6.0f} {s(sr['client'])[:16]:16} "
              f"{s(sr['country'])[:8]:8} {s(sr['produs'])[:16]:16} "
              f"{s(sr['period'])[:2]:>2} {mrr[:3]:3} {s(sr['start']):10} "
              f"{' '.join(flags)}")
    print(f"\nNet new monthly MRR from candidates: EUR {tot:,.0f}")


if __name__ == "__main__":
    main()
