"""Meta-evaluation: how accurate is the judge?

An LLM judge is a classifier, so we measure it like one: on answers whose true label we know.

Labelled items come from two places:
1. Natural: real answers from recorded runs, labelled by a person (labels.jsonl).
2. Synthetic: answers labelled good are corrupted in known ways, so the label is "bad" by
   construction:
     number_swap  a number from the reference answer is changed (Rs 25,000 -> Rs 37,500)
     flip         a condition is reversed (at least -> at most, before -> after)
     injected     a plausible claim that no policy document contains is appended

For each judge we report the catch rate (bad answers flagged), the false-alarm rate (good answers
flagged) and Cohen's kappa (agreement beyond chance).
"""

import re
import zlib
from pathlib import Path

from .judges import PROMPT_VERSIONS, Judges
from .metrics import normalize
from .runner import read_jsonl
from .stats import cohen_kappa
from .suite import Suite

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

FLIPS = [("at least", "at most"), ("at most", "at least"), ("minimum", "maximum"), ("maximum", "minimum"),
         ("before", "after"), ("more than", "less than"), ("above", "below"), ("never", "always"),
         ("up to", "at least"), ("within", "after"), ("only after", "only before")]

# Plausible lending-policy statements that appear in none of the policy documents (checked in tests).
UNSUPPORTED_CLAIMS = [
    "Customers who hold a Northwind salary account also get a 0.25% interest rate discount.",
    "Senior citizens above 60 are given priority processing.",
    "Existing customers with a clean repayment record can have this limit raised by 10%.",
    "A one-time documentation fee of Rs 750 also applies.",
    "Requests can also be submitted at any Northwind branch on Saturdays.",
    "The branch manager can approve exceptions to this rule.",
    "Women applicants get this waived under the Udyam scheme.",
    "A gold-backed top-up loan is also available for this.",
]


def _key(x: float) -> str:
    """Canonical text for a number: 2250000.0 -> "2250000", 1.5 -> "1.5"."""
    return str(int(x)) if x == int(x) else f"{x:g}"


def indian_format(n: int) -> str:
    """1500000 -> 15,00,000 (Indian digit grouping)."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *groups, tail]) if head else ",".join([*groups, tail])


def _fmt(raw: str, value: float) -> str:
    if value != int(value):
        return _key(value)
    n = int(value)
    if "," not in raw:
        return str(n)
    if re.search(r",\d\d,", raw) or (raw.count(",") == 1 and n >= 100000):
        return indian_format(n)  # the original used lakh grouping (15,00,000), keep that style
    return f"{n:,}"


def swap_number(answer: str, protected: set[str], forbidden: set[str]) -> tuple[str, str, str] | None:
    """Change the first number in `answer` that is one of `protected` (numbers from the reference) to a
    nearby value that appears nowhere in `forbidden` (numbers in the retrieved context)."""
    for m in NUMBER.finditer(answer):
        raw = m.group().rstrip(",")
        if answer[max(0, m.start() - 1):m.start()] == "[":  # a citation marker like [2]
            continue
        val = _key(float(raw.replace(",", "")))
        if val not in protected:
            continue
        x = float(val)
        for cand in (x * 1.5, x + 2, x * 2, x + 1):
            # whole numbers stay whole (a real hallucination says "32 years", not "31.5 years")
            cand = float(int(cand + 0.5)) if x == int(x) else round(cand, 2)
            key = _key(cand)
            if key != val and key not in forbidden:
                new = _fmt(raw, cand)
                return answer[:m.start()] + new + answer[m.start() + len(raw):], raw, new
    return None


def flip_condition(answer: str) -> tuple[str, str, str] | None:
    for old, new in FLIPS:
        m = re.search(rf"\b{re.escape(old)}\b", answer, flags=re.I)
        if m:
            found = m.group()
            repl = new[0].upper() + new[1:] if found[0].isupper() else new
            return answer[:m.start()] + repl + answer[m.end():], found, repl
    return None


def inject_claim(answer: str, key: str) -> tuple[str, str]:
    claim = UNSUPPORTED_CLAIMS[zlib.crc32(key.encode()) % len(UNSUPPORTED_CLAIMS)]
    return f"{answer.rstrip()} {claim}", claim


def numbers(text: str) -> set[str]:
    return {_key(float(n.replace(",", ""))) for n in (m.rstrip(",") for m in NUMBER.findall(normalize(text))) if n}


def build_items(suite: Suite, run_dirs: list[Path], labels_path: Path) -> list[dict]:
    cases = {c.id: c for c in suite.cases}
    outputs = {(d.name, r["id"]): r["output"] for d in run_dirs for r in read_jsonl(d / "outputs.jsonl")}
    items, rotation = [], 0
    for lab in read_jsonl(labels_path):
        out = outputs.get((lab["run"], lab["id"]))
        if out is None or not out["answered"]:
            continue
        case = cases[lab["id"]]
        base = {"run": lab["run"], "id": lab["id"], "question": case.input, "contexts": out["contexts"],
                "reference": case.reference, "note": lab.get("note", "")}
        if lab.get("faithful") is not None:
            items.append({**base, "kind": "faithfulness", "source": "natural", "answer": out["answer"], "label": lab["faithful"]})
        if lab.get("correct") is not None and case.reference:
            items.append({**base, "kind": "correctness", "source": "natural", "answer": out["answer"], "label": lab["correct"]})
        if not (lab.get("faithful") and lab.get("correct") and case.reference):
            continue  # only corrupt answers known to be good

        # Correctness: change a number the reference depends on.
        ctx_numbers = numbers(" ".join(out["contexts"]))
        swap = swap_number(out["answer"], numbers(case.reference), ctx_numbers)
        if swap:
            items.append({**base, "kind": "correctness", "source": "number_swap", "answer": swap[0], "label": False,
                          "note": f"{swap[1]} -> {swap[2]}"})
        # Faithfulness: one corruption per answer, rotating through the three kinds.
        options = {"number_swap": swap, "flip": flip_condition(out["answer"]),
                   "injected": inject_claim(out["answer"], lab["id"])}
        order = ["number_swap", "flip", "injected"]
        for k in order[rotation % 3:] + order[:rotation % 3]:
            if options[k]:
                o = options[k]
                items.append({**base, "kind": "faithfulness", "source": k, "answer": o[0], "label": False,
                              "note": f"{o[1]} -> {o[2]}" if k != "injected" else f"added: {o[1]}"})
                rotation += 1
                break
    return items


def stratified_sample(items: list[dict], n: int) -> list[dict]:
    """A deterministic sample that keeps every (task, source, label) group in proportion: every k-th item
    of each group, so a slow judge can be measured on fewer items without skewing the mix."""
    if n >= len(items):
        return items
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        groups.setdefault((it["kind"], it["source"], it["label"]), []).append(it)
    picked = []
    for g in groups.values():
        k = max(1, round(len(g) * n / len(items)))
        step = len(g) / k
        picked += [g[int(i * step)] for i in range(k)]
    return [it for it in items if any(it is p for p in picked)]


def run_meta_eval(items: list[dict], judges: Judges, log=print) -> dict:
    for it in items:
        if it["kind"] == "faithfulness":
            res = judges.faithfulness(it["question"], it["answer"], it["contexts"], it["id"])
        else:
            res = judges.correctness(it["question"], it["answer"], it["reference"], it["id"])
        it["pred"] = res.passed
        it["judge_details"] = res.details
        it["judge_error"] = res.error
        mark = "ok " if res.passed == it["label"] else ("ERR" if res.passed is None else "XX ")
        log(f"  {mark} {it['kind'][:7]} {it['source']:11s} {it['run']}/{it['id']} label={it['label']} judge={res.passed}")
    return {"judge": judges.llm.config.model, "prompt_versions": PROMPT_VERSIONS,
            "summary": summarize(items), "items": items}


def summarize(items: list[dict]) -> dict:
    out = {}
    for kind in ("faithfulness", "correctness"):
        its = [i for i in items if i["kind"] == kind]
        ok = [i for i in its if i["pred"] is not None]
        if not ok:
            continue
        bad = [i for i in ok if not i["label"]]
        good = [i for i in ok if i["label"]]
        by_source = {}
        for src in sorted({i["source"] for i in ok}):
            s = [i for i in ok if i["source"] == src]
            by_source[src] = {"n": len(s), "agree": sum(i["pred"] == i["label"] for i in s),
                              "bad": sum(not i["label"] for i in s), "good": sum(bool(i["label"]) for i in s)}
        out[kind] = {
            "n": len(ok), "judge_errors": len(its) - len(ok),
            "accuracy": sum(i["pred"] == i["label"] for i in ok) / len(ok),
            "catch_rate": sum(not i["pred"] for i in bad) / len(bad) if bad else None,
            "false_alarm_rate": sum(not i["pred"] for i in good) / len(good) if good else None,
            "kappa": cohen_kappa([i["label"] for i in ok], [i["pred"] for i in ok]),
            "by_source": by_source,
        }
    return out


def to_markdown(result: dict) -> str:
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    out = [f"# Judge meta-evaluation: `{result['judge']}`", "",
           "| Judge task | Items | Accuracy | Catch rate (bad flagged) | False alarms (good flagged) | Cohen's kappa | Judge errors |",
           "|---|---|---|---|---|---|---|"]
    for kind, s in result["summary"].items():
        out.append(f"| {kind} | {s['n']} | {pct(s['accuracy'])} | {pct(s['catch_rate'])} | "
                   f"{pct(s['false_alarm_rate'])} | {s['kappa']:.2f} | {s['judge_errors']} |")
    out += ["", "## By source", "", "| Judge task | Source | Items (good / bad) | Judge agrees |", "|---|---|---|---|"]
    for kind, s in result["summary"].items():
        for src, b in s["by_source"].items():
            out.append(f"| {kind} | {src} | {b['n']} ({b['good']} / {b['bad']}) | {b['agree']}/{b['n']} |")
    wrong = [i for i in result["items"] if i["pred"] is not None and i["pred"] != i["label"]]
    if wrong:
        out += ["", "## Disagreements with the label", ""]
        for i in wrong:
            why = ""
            d = i.get("judge_details") or {}
            if i["kind"] == "faithfulness":
                bad = [c["claim"] for c in d.get("claims", []) if not c.get("supported")]
                why = "; unsupported per judge: " + " | ".join(bad) if bad else "; judge found every claim supported"
            else:
                bad = [f"{f['fact']} ({f['status']})" for f in d.get("facts", []) if f.get("status") != "stated"]
                why = "; judge: " + " | ".join(bad) if bad else "; judge found every fact stated"
            note = f" [{i['note']}]" if i.get("note") else ""
            out.append(f"- `{i['run']}/{i['id']}` {i['kind']} / {i['source']}{note}: label "
                       f"{'good' if i['label'] else 'bad'}, judge {'good' if i['pred'] else 'bad'}{why}")
    return "\n".join(out) + "\n"
