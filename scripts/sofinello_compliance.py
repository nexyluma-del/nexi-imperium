#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DISCLAIMER = Path("/mnt/c/AI/projects/06-heilung/knowledge/disclaimer-standard.md")


DISEASE_TERMS = [
    "krebs",
    "tumor",
    "diabetes",
    "bluthochdruck",
    "asthma",
    "copd",
    "arthritis",
    "rheuma",
    "depression",
    "angststoerung",
    "alzheimer",
    "demenz",
    "infektion",
    "virus",
    "bakterien",
    "parasiten",
    "nierenerkrankung",
    "lebererkrankung",
    "herzinfarkt",
    "schlaganfall",
]

CLAIM_VERBS = [
    "heilt",
    "heilen",
    "geheilt",
    "kuriert",
    "kurieren",
    "beseitigt",
    "behandelt",
    "therapiert",
    "verhindert",
    "vorbeugt",
    "lindert",
    "stoppt",
    "toetet",
    "bekämpft",
    "bekaempft",
]

SAFE_LINE_MARKERS = [
    "keine",
    "nicht",
    "verbot",
    "risiko",
    "warn",
    "disclaimer",
    "compliance",
    "behaupt",
    "sagt",
    "video stellt",
    "sebi vertrat",
    "traditionell",
    "nicht bestaetigt",
    "nicht bestätigt",
]

ATTENTION_TERMS = [
    "dosierung",
    "dosis",
    "taeglich",
    "täglich",
    "krankheit",
    "symptom",
    "entgift",
    "detox",
    "parasiten",
    "schleim",
    "diagnose",
]


def read_disclaimer(path: Path = DEFAULT_DISCLAIMER) -> str:
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        return re.sub(r"^# .+?\n+", "", text, count=1, flags=re.S).strip()
    return (
        "Diese Analyse dient der internen Sichtung und ist keine medizinische Beratung, "
        "keine Diagnose und keine Behandlungsempfehlung. Oeffentliche Nutzung erfordert "
        "fachliche und rechtliche Pruefung."
    )


def line_is_safe_context(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in SAFE_LINE_MARKERS)


def scan_claims(text: str) -> dict[str, Any]:
    disease_pattern = "|".join(re.escape(term) for term in DISEASE_TERMS)
    claim_pattern = "|".join(re.escape(term) for term in CLAIM_VERBS)
    hard_regexes = [
        re.compile(rf"\b({claim_pattern})\b.{{0,90}}\b({disease_pattern})\b", re.I),
        re.compile(rf"\b({disease_pattern})\b.{{0,90}}\b({claim_pattern})\b", re.I),
        re.compile(r"\b(ersetzt|statt)\b.{0,70}\b(arzt|aerzt|medikament|therapie)\b", re.I),
        re.compile(r"\b(du hast|sie haben)\b.{0,80}\b(krankheit|syndrom|infektion|mangel)\b", re.I),
        re.compile(r"\b(100\s*%|garantiert|sicher)\b.{0,80}\b(wirkt|wirkung|ergebnis|heil)", re.I),
    ]

    hard_findings: list[dict[str, str]] = []
    attention: list[dict[str, str]] = []

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        for regex in hard_regexes:
            if regex.search(stripped) and not line_is_safe_context(stripped):
                hard_findings.append({"line": str(number), "text": stripped[:500]})
                break
        for term in ATTENTION_TERMS:
            if term in lowered:
                attention.append({"line": str(number), "term": term, "text": stripped[:350]})
                break

    status = "FREIGEGEBEN"
    if hard_findings:
        status = "BLOCKIERT"

    return {
        "status": status,
        "hard_findings": hard_findings,
        "attention_findings": attention[:40],
        "hard_count": len(hard_findings),
        "attention_count": len(attention),
    }


def sanitize_claim_language(text: str) -> str:
    sanitized = text
    replacements = {
        r"\bheilt\b": "[verbotene Heilclaim-Formulierung]",
        r"\bheilen\b": "[verbotene Heilclaim-Formulierung]",
        r"\bgeheilt\b": "[verbotene Heilclaim-Formulierung]",
        r"\bkuriert\b": "[verbotene Heilclaim-Formulierung]",
        r"\bkurieren\b": "[verbotene Heilclaim-Formulierung]",
        r"\bbehandelt\b": "[verbotene Behandlungsclaim-Formulierung]",
        r"\btherapiert\b": "[verbotene Therapieclaim-Formulierung]",
        r"\bbeseitigt\b": "[verbotene Wirkclaim-Formulierung]",
        r"\bverhindert\b": "[verbotene Praeventionsclaim-Formulierung]",
        r"\bvorbeugt\b": "[verbotene Praeventionsclaim-Formulierung]",
        r"\blindert\b": "[verbotene Linderungsclaim-Formulierung]",
    }
    for pattern, replacement in replacements.items():
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.I)
    return sanitized


def compliance_block(result: dict[str, Any], disclaimer: str) -> str:
    hard_lines = "\n".join(
        f"- Zeile {item['line']}: {item['text']}" for item in result.get("hard_findings", [])
    ) or "- Keine blockierenden Heil-/Diagnose-Claims gefunden."
    attention_lines = "\n".join(
        f"- Zeile {item['line']}: {item['term']}" for item in result.get("attention_findings", [])[:12]
    ) or "- Keine besonderen Aufmerksamkeitsterme gefunden."
    return "\n".join(
        [
            "## Compliance-Check",
            "",
            f"Status: {result['status']}",
            f"Geprueft am: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "### Pflicht-Disclaimer",
            "",
            disclaimer,
            "",
            "### Blockierende Funde",
            "",
            hard_lines,
            "",
            "### Aufmerksamkeitsterme",
            "",
            attention_lines,
            "",
            "### Freigabe-Regel",
            "",
            "- Oeffentliche Nutzung erst nach fachlicher/rechtlicher Pruefung.",
            "- Keine Heilversprechen, keine Diagnosen, keine krankheitsbezogene Werbung.",
            "- Traditionelle/Sebi-nahe Aussagen nur als solche kennzeichnen.",
            "",
        ]
    )


def apply_compliance(input_md: Path, output_md: Path, disclaimer_file: Path = DEFAULT_DISCLAIMER) -> dict[str, Any]:
    text = input_md.read_text(encoding="utf-8")
    disclaimer = read_disclaimer(disclaimer_file)
    result = scan_claims(text)
    safe_text = sanitize_claim_language(text)
    for group in ("hard_findings", "attention_findings"):
        for item in result.get(group, []):
            if "text" in item:
                item["text"] = sanitize_claim_language(item["text"])
    final_text = "\n\n".join([safe_text.rstrip(), compliance_block(result, disclaimer)])
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(final_text + "\n", encoding="utf-8")
    result.update(
        {
            "input_markdown": str(input_md),
            "output_markdown": str(output_md),
            "disclaimer_file": str(disclaimer_file),
        }
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sofinello compliance check on a Markdown analysis.")
    parser.add_argument("input_md", type=Path)
    parser.add_argument("--output-md", type=Path, default=None)
    parser.add_argument("--disclaimer-file", type=Path, default=DEFAULT_DISCLAIMER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_md = args.output_md or args.input_md.with_name(args.input_md.stem + ".compliance.md")
    result = apply_compliance(args.input_md, output_md, args.disclaimer_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "FREIGEGEBEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
