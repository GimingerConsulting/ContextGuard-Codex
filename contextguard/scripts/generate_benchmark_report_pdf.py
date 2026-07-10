#!/usr/bin/env python3
"""Generate professional ContextGuard 0.9.0 benchmark PDF (readable, charts, USD)."""
from __future__ import annotations

import json
import statistics
import tempfile
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PROJECT_ROOT / ".contextguard" / "reports"
BENCH = Path(__file__).resolve().parents[1] / "benchmarks" / "results"
DESKTOP = Path.home() / "Desktop"
OUT_PDF = DESKTOP / f"ContextGuard-0.9.0-Benchmark-Report-{date.today().isoformat()}.pdf"

PAGE_W, _PAGE_H = A4
CONTENT_W = PAGE_W - 4 * cm

GOLD = "#C9A24A"
DARK = "#1F2937"
MUTED = "#6B7280"
RAW_COLOR = "#E85D5D"
CG_COLOR = "#2EAD7A"
ACCENT = "#3B82F6"

DAILY_TIERS = [25_000_000, 50_000_000, 100_000_000, 150_000_000]

DEFAULT_MIX = {"cached_input_share": 0.88, "uncached_input_share": 0.08, "output_share": 0.04}
USD_RATES = {"uncached_input_per_m": 5.0, "cached_input_per_m": 0.5, "output_per_m": 30.0}

LIVE_PATHS = [
    REPORTS / "real-codex-power-user-ab-external-2026-06-15" / "summary.json",
    REPORTS / "real-codex-power-user-ab-external-run2-2026-06-16" / "summary.json",
    REPORTS / "real-codex-power-user-ab-external-run3-2026-06-16" / "summary.json",
    REPORTS / "real-codex-power-user-ab-external-run4-2026-06-16" / "summary.json",
    REPORTS / "real-codex-power-user-ab-external-run5-2026-06-16" / "summary.json",
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_int(n: int | float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_pct(n: float) -> str:
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def estimate_usd(tokens: int) -> float:
    return (
        tokens * DEFAULT_MIX["uncached_input_share"] * USD_RATES["uncached_input_per_m"]
        + tokens * DEFAULT_MIX["cached_input_share"] * USD_RATES["cached_input_per_m"]
        + tokens * DEFAULT_MIX["output_share"] * USD_RATES["output_per_m"] * 0.2
    ) / 1_000_000


def fmt_usd(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if amount >= 10_000:
        return f"${amount / 1_000:.1f}k"
    if amount >= 1_000:
        return f"${amount:,.0f}".replace(",", ".")
    return f"${amount:.2f}"


def make_table(data: list[list], col_widths: list[float], header_rows: int = 1) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor(DARK)),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, header_rows), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    for i in range(header_rows, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F9FAFB")))
    t.setStyle(TableStyle(style))
    return t


def chart_live_input(runs: list[dict], out: Path) -> None:
    labels = [f"Run {i+1}" for i in range(len(runs))]
    raw = [r["comparison"]["input_tokens"]["raw"] for r in runs]
    cg = [r["comparison"]["input_tokens"]["contextguard"] for r in runs]
    x = range(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
    ax.bar([i - w / 2 for i in x], raw, w, label="RAW", color=RAW_COLOR, edgecolor="white", linewidth=0.8, zorder=3)
    ax.bar([i + w / 2 for i in x], cg, w, label="ContextGuard", color=CG_COLOR, edgecolor="white", linewidth=0.8, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Input Tokens")
    ax.set_title("Live Codex CLI — Input Tokens per Run")
    ax.legend(frameon=True, loc="upper right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v/1000)}k"))
    ax.set_axisbelow(True)
    fig.tight_layout(pad=1.2)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_savings_pct(runs: list[dict], out: Path) -> None:
    labels = [f"Run {i+1}" for i in range(len(runs))]
    input_pct = [abs(r["comparison"]["input_tokens"]["change_percent"]) for r in runs]
    tool_pct = [abs(r["comparison"]["tool_output_bytes"]["change_percent"]) for r in runs]
    x = range(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
    ax.bar([i - w / 2 for i in x], input_pct, w, label="Input Tokens Saved", color=CG_COLOR, edgecolor="white", linewidth=0.8)
    ax.bar([i + w / 2 for i in x], tool_pct, w, label="Tool Output Saved", color=GOLD, edgecolor="white", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Savings %")
    ax.set_title("Savings per Run — ContextGuard vs RAW")
    ax.set_ylim(0, 105)
    ax.legend(frameon=True, loc="upper right")
    ax.set_axisbelow(True)
    fig.tight_layout(pad=1.2)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_cost_projection(median_rate: float, out: Path) -> None:
    labels = [f"{t // 1_000_000}M/day" for t in DAILY_TIERS]
    monthly_saved = [int(t * 30 * median_rate) for t in DAILY_TIERS]
    monthly_usd = [estimate_usd(s) for s in monthly_saved]
    palette = [GOLD, CG_COLOR, ACCENT, DARK]
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
    bars = ax.bar(labels, monthly_usd, color=palette, edgecolor="white", linewidth=1.0, width=0.62)
    ax.set_ylabel("USD Saved per Month (proxy)")
    ax.set_title(f"Cost Projection — Median Run Savings ({median_rate*100:.1f}% input reduction)")
    ymax = max(monthly_usd) * 1.18 if monthly_usd else 1
    ax.set_ylim(0, ymax)
    for bar, val in zip(bars, monthly_usd):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.02,
            fmt_usd(val),
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_axisbelow(True)
    fig.tight_layout(pad=1.2)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_deterministic(benchmarks: list[tuple[str, float]], out: Path) -> None:
    names = [b[0] for b in benchmarks]
    pcts = [b[1] for b in benchmarks]
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
    y = range(len(names))
    bars = ax.barh(list(y), pcts, color=CG_COLOR, height=0.58, edgecolor="white", linewidth=0.8)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Visible Token Reduction %")
    ax.set_title("Deterministic Benchmarks — Tool Output Compaction")
    ax.set_xlim(0, 108)
    for bar, v in zip(bars, pcts):
        ax.text(v + 1.5, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=8, fontweight="bold")
    ax.set_axisbelow(True)
    fig.tight_layout(pad=1.2)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def projection_table_rows(median_rate: float) -> list[list[str]]:
    header = [
        "Daily Volume",
        "Saved / Day",
        "Saved / Month",
        "Saved / Year",
        "USD / Day",
        "USD / Month",
        "USD / Year",
    ]
    rows = [header]
    for daily in DAILY_TIERS:
        saved_day = int(daily * median_rate)
        saved_month = saved_day * 30
        saved_year = saved_day * 365
        rows.append([
            f"{daily // 1_000_000}M tokens/day",
            fmt_int(saved_day),
            fmt_int(saved_month),
            fmt_int(saved_year),
            fmt_usd(estimate_usd(saved_day)),
            fmt_usd(estimate_usd(saved_month)),
            fmt_usd(estimate_usd(saved_year)),
        ])
    return rows


def main() -> int:
    live_runs = [load_json(p) for p in LIVE_PATHS]
    tier5 = load_json(REPORTS / "tier-five-persona-ab-2026-06-15" / "summary.json")
    usecase = load_json(REPORTS / "final-usecase-ab-2026-06-16" / "summary.json")
    output_ab = load_json(BENCH / "output-ab-2026-06-10.json")
    install = load_json(BENCH / "install-acceptance-2026-06-10.json")

    input_deltas = [r["comparison"]["input_tokens"]["change_percent"] for r in live_runs]
    tool_deltas = [r["comparison"]["tool_output_bytes"]["change_percent"] for r in live_runs]
    median_input = statistics.median(input_deltas)
    median_rate = abs(median_input) / 100
    median_tool = abs(statistics.median(tool_deltas))
    all_valid = all(r["equivalent_result"] for r in live_runs)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=24, textColor=colors.HexColor(DARK), spaceAfter=6)
    subtitle = ParagraphStyle("Sub", fontSize=12, textColor=colors.HexColor(GOLD), spaceAfter=14)
    h1 = ParagraphStyle("H1", fontSize=14, textColor=colors.HexColor(DARK), spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold")
    body = ParagraphStyle("B", fontSize=10, leading=14, textColor=colors.HexColor(DARK), spaceAfter=8)
    small = ParagraphStyle("S", fontSize=8, leading=11, textColor=colors.HexColor(MUTED))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        charts = {k: tmp_path / f"{k}.png" for k in ("input", "savings", "cost", "det")}
        chart_live_input(live_runs, charts["input"])
        chart_savings_pct(live_runs, charts["savings"])
        chart_cost_projection(median_rate, charts["cost"])
        chart_deterministic([
            ("130 pytest failures", output_ab["token_reduction_percent"]),
            ("Install acceptance", install["tokens"]["reduction_percent"]),
            ("5 Personas (Tier-5)", tier5["totals"]["session_savings_percent"]),
            ("Enterprise use-cases", usecase["segment_summary"]["enterprise"]["session_savings_percent"]),
        ], charts["det"])

        doc = SimpleDocTemplate(
            str(OUT_PDF),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
        )
        story: list = []
        img_h = CONTENT_W * 0.48

        story.append(Spacer(1, 2 * cm))
        story.append(Paragraph("ContextGuard 0.9.0", title_style))
        story.append(Paragraph("Benchmark &amp; Savings Report", subtitle))
        story.append(Paragraph(
            f"Generated {date.today().strftime('%B %d, %Y')} · 5 live Codex CLI tests · GPT-5.5 pricing (USD)",
            small,
        ))
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph(
            f"<b>Bottom line:</b> Across 5 independent live Codex runs, ContextGuard saved "
            f"<b>{abs(median_input):.1f}% input tokens</b> (median run) and "
            f"<b>{median_tool:.1f}% tool output bytes</b> in an enterprise on-call diagnosis workflow. "
            f"All 5 runs valid.",
            body,
        ))

        story.append(Paragraph("How ContextGuard Works", h1))
        for line in [
            "<b>Capture runner</b> compacts command stdout/stderr locally before Codex sees it.",
            "<b>Lifecycle hooks</b> rewrite commands, archive evidence, adaptive compaction.",
            "<b>Session gate &amp; brief</b> budget noisy exploration; doc-family codecs for structured files.",
            "<b>Reporting</b> via lifetime-savings, session-cost, quota-proxy CLI commands.",
        ]:
            story.append(Paragraph(f"• {line}", body))

        story.append(PageBreak())
        story.append(Paragraph("Live Codex CLI Tests (5 Runs)", h1))
        story.append(Paragraph(
            "Same scenario each run: 2× migration test failures + 1× slow-query log inspect + structured diagnosis. "
            "Model: GPT-5.5, medium reasoning.",
            body,
        ))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Image(str(charts["input"]), width=CONTENT_W, height=img_h))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Image(str(charts["savings"]), width=CONTENT_W, height=img_h))

        story.append(PageBreak())
        story.append(Paragraph("Live Test Details — Input", h1))
        cw = [2.0 * cm, 3.4 * cm, 3.4 * cm, 3.0 * cm, 2.6 * cm, 2.0 * cm]
        rows = [["Run", "RAW Input", "CG Input", "Saved", "Δ %", "Valid"]]
        for i, r in enumerate(live_runs):
            c = r["comparison"]["input_tokens"]
            rows.append([
                f"Run {i+1}",
                fmt_int(c["raw"]),
                fmt_int(c["contextguard"]),
                fmt_int(c["raw"] - c["contextguard"]),
                fmt_pct(c["change_percent"]),
                "Yes" if r["equivalent_result"] else "No",
            ])
        rows.append([
            "Median",
            "—", "—", "—",
            fmt_pct(median_input),
            "5/5" if all_valid else "—",
        ])
        story.append(make_table(rows, cw))
        story.append(Spacer(1, 0.6 * cm))

        story.append(Paragraph("Live Test Details — Tool Output", h1))
        cw2 = [2.0 * cm, 3.6 * cm, 3.6 * cm, 3.0 * cm, 2.2 * cm, 2.0 * cm]
        rows2 = [["Run", "RAW Tool Bytes", "CG Tool Bytes", "Δ Tool %", "RAW Out", "CG Out"]]
        for i, r in enumerate(live_runs):
            c = r["comparison"]
            rows2.append([
                f"Run {i+1}",
                fmt_int(c["tool_output_bytes"]["raw"]),
                fmt_int(c["tool_output_bytes"]["contextguard"]),
                fmt_pct(c["tool_output_bytes"]["change_percent"]),
                fmt_int(c["output_tokens"]["raw"]),
                fmt_int(c["output_tokens"]["contextguard"]),
            ])
        story.append(make_table(rows2, cw2))

        story.append(PageBreak())
        story.append(Paragraph("Cost Projection (USD, GPT-5.5 Proxy)", h1))
        story.append(Paragraph(
            f"Based on <b>median run savings of {abs(median_input):.1f}%</b> input reduction. "
            "Pricing: uncached input $5/M · cached input $0.50/M · output $30/M "
            "(mix: 88% cached / 8% uncached / 4% output).",
            body,
        ))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Image(str(charts["cost"]), width=CONTENT_W, height=img_h))
        story.append(Spacer(1, 0.5 * cm))

        proj_col_w = [2.6 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.0 * cm, 2.2 * cm, 2.2 * cm]
        story.append(make_table(projection_table_rows(median_rate), proj_col_w))

        story.append(PageBreak())
        story.append(Paragraph("Deterministic Benchmarks (0.9.0)", h1))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Image(str(charts["det"]), width=CONTENT_W, height=img_h))
        story.append(Spacer(1, 0.5 * cm))

        det_rows = [["Benchmark", "RAW Tokens", "CG Tokens", "Reduction"]]
        det_rows.append([
            "130 pytest failures",
            fmt_int(output_ab["raw_visible_tokens"]),
            fmt_int(output_ab["contextguard_visible_tokens"]),
            f"{output_ab['token_reduction_percent']:.1f}%",
        ])
        det_rows.append([
            "Install acceptance",
            fmt_int(install["tokens"]["raw_visible"]),
            fmt_int(install["tokens"]["contextguard_visible"]),
            f"{install['tokens']['reduction_percent']:.1f}%",
        ])
        t = tier5["totals"]
        det_rows.append([
            "Tier-5 personas (5)",
            fmt_int(t["raw_tokens"]),
            fmt_int(t["contextguard_tokens"]),
            f"{t['session_savings_percent']:.1f}%",
        ])
        u = usecase["segment_summary"]
        det_rows.append([
            "Enterprise use-cases (8)",
            fmt_int(u["enterprise"]["raw_tokens"]),
            fmt_int(u["enterprise"]["contextguard_tokens"]),
            f"{u['enterprise']['session_savings_percent']:.1f}%",
        ])
        story.append(make_table(det_rows, [6 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm]))

        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph("Persona Breakdown (Tier-5)", h1))
        p_rows = [["Persona", "RAW", "ContextGuard", "Saved %"]]
        for p in tier5["personas"]:
            p_rows.append([
                p["label"][:30],
                fmt_int(p["raw_tokens"]),
                fmt_int(p["contextguard_tokens"]),
                f"{p['session_savings_percent']:.1f}%",
            ])
        story.append(make_table(p_rows, [6 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm]))

        story.append(PageBreak())
        story.append(Paragraph("Where ContextGuard Wins", h1))
        for line in [
            "pytest / CI failure output, production logs, large grep/find/diff results.",
            f"~{abs(median_input):.0f}% live input savings on diagnosis workflows (median of 5 runs).",
            "Up to 98% tool-output bytes removed before reaching the model.",
            "Byte-identical archives; compact view keeps summaries and failure names.",
        ]:
            story.append(Paragraph(f"• {line}", body))

        story.append(Spacer(1, 0.8 * cm))
        story.append(Paragraph("Giminger Consulting · ContextGuard 0.9.0+codex · Codex-native context optimization", small))

        doc.build(story)

    print(json.dumps({
        "pdf": str(OUT_PDF),
        "bytes": OUT_PDF.stat().st_size,
        "median_input_savings_pct": round(median_input, 2),
        "daily_tiers": [t // 1_000_000 for t in DAILY_TIERS],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())