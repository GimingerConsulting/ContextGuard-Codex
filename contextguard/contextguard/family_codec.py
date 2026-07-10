from __future__ import annotations


def encode_family_entries(family: str, entries: list[dict[str, object]]) -> list[str]:
    if not entries:
        return []
    canonical = entries[0]
    lines = [
        (
            f"- {family}: canonical={canonical['path']} sha={canonical['sha256']} "
            f"tokens~{canonical['tokens_est']}"
        )
    ]
    for entry in entries[1:]:
        delta_tokens = int(entry.get("tokens_est", 0)) - int(canonical.get("tokens_est", 0))
        lines.append(
            f"  delta:{entry['path']} sha={entry['sha256']} Δtokens~{delta_tokens:+d} "
            "expand=only_if_canonical_insufficient"
        )
    return lines


def render_family_codec_brief(
    families: dict[str, list[dict[str, object]]],
    *,
    budget_lines: int = 14,
) -> str:
    if not families:
        return ""
    lines = ["ContextGuard doc family codec (canonical-first; expand deltas only when needed):"]
    for family, entries in families.items():
        lines.extend(encode_family_entries(family, entries))
        if len(lines) >= budget_lines:
            break
    if len(lines) >= budget_lines:
        lines.append("- ... additional families truncated")
    return "\n".join(lines)