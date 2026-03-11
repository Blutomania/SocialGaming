#!/usr/bin/env python3
"""
Choose Your Mystery — CLI
=========================

Terminal interface for mystery generation and analysis.
Emulates the MysterySolver interactive UX in a rich terminal environment.

Commands:
    mystery generate    — Generate a new mystery with part-tracked RAG
    mystery solve       — Analyze a mystery scenario (MysterySolver mode)
    mystery list        — Browse the mystery database
    mystery registry    — Inspect the part registry and diversity stats
    mystery extract     — Run corpus extraction pipeline

Usage:
    python cli.py generate
    python cli.py generate --setting "Ancient Athens, agora marketplace" --demo
    python cli.py solve
    python cli.py list
    python cli.py registry
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ── Rich terminal UI ─────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.rule import Rule
    from rich.text import Text
    from rich import box

    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def _print(text: str, style: str = ""):
    if HAS_RICH:
        console.print(text, style=style if style else None)
    else:
        # Strip rich markup for plain output
        import re
        clean = re.sub(r"\[/?[^\]]*\]", "", text)
        print(clean)


def _panel(content: str, title: str = "", border: str = "white"):
    if HAS_RICH:
        console.print(Panel(content, title=title, border_style=border, padding=(0, 2)))
    else:
        import re
        clean_title = re.sub(r"\[/?[^\]]*\]", "", title)
        clean_body = re.sub(r"\[/?[^\]]*\]", "", content)
        print(f"\n── {clean_title} " + "─" * max(0, 60 - len(clean_title)))
        print(clean_body)
        print("─" * 62)


def _rule(title: str = ""):
    if HAS_RICH:
        console.rule(title)
    else:
        import re
        clean = re.sub(r"\[/?[^\]]*\]", "", title)
        print("\n" + "─" * 20 + f" {clean} " + "─" * 20)


def _ask(prompt: str, default: str = "") -> str:
    if HAS_RICH:
        return Prompt.ask(prompt, default=default)
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def _ask_int(prompt: str, default: int = 4) -> int:
    if HAS_RICH:
        return IntPrompt.ask(prompt, default=default)
    val = input(f"{prompt} [{default}]: ").strip()
    return int(val) if val.isdigit() else default


def _confirm(prompt: str, default: bool = True) -> bool:
    if HAS_RICH:
        return Confirm.ask(prompt, default=default)
    suffix = " [Y/n]" if default else " [y/N]"
    val = input(f"{prompt}{suffix}: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


def _spinner(message: str):
    """Context manager: show a spinner while work happens."""
    if HAS_RICH:
        return console.status(f"[cyan]{message}[/cyan]")
    else:
        class _NoOp:
            def __enter__(self): print(message); return self
            def __exit__(self, *_): pass
        return _NoOp()


# ============================================================================
# BANNER
# ============================================================================

BANNER_TEXT = """\
  ╔══════════════════════════════════════════════════════════════╗
  ║     ░▒▓  CHOOSE YOUR MYSTERY  ▓▒░                           ║
  ║     Mystery Generation Engine · Part-Tracked RAG            ║
  ║     Auditable Recipes · Diversity-Constrained Sampling       ║
  ╚══════════════════════════════════════════════════════════════╝"""


def _banner():
    if HAS_RICH:
        console.print(
            Panel(
                "[bold cyan]CHOOSE YOUR MYSTERY[/bold cyan]\n"
                "[dim]Mystery Generation Engine  ·  Part-Tracked RAG  ·  Auditable Recipes[/dim]",
                border_style="cyan",
                padding=(1, 6),
            )
        )
    else:
        print(BANNER_TEXT)


# ============================================================================
# REGISTRY LOADING
# ============================================================================

def _load_registry(db_dir: str):
    from part_registry import load_registry
    return load_registry(db_dir)


# ============================================================================
# COMMAND: generate
# ============================================================================

def cmd_generate(args):
    """
    Generate a new mystery with part-level RAG + diversity constraint.

    Flow:
        1. Collect setting / crime type / players interactively
        2. Load part registry (bootstraps from test corpus if empty)
        3. Infer setting period/environment, filter compatible parts
        4. Sample with max_per_source diversity constraint
        5. Show selected parts table
        6. Call Claude (or demo) to synthesize
        7. Display mystery + provenance recipe C(4) + F(2) + A(6)...
    """
    _banner()
    _print("\n[bold yellow]⚙  MYSTERY GENERATOR[/bold yellow]\n")

    # ── Collect inputs ────────────────────────────────────────────────
    setting = args.setting
    if not setting:
        setting = _ask(
            "[cyan]Setting[/cyan] [dim](e.g. 'Ancient Athens, agora marketplace, 400 BC')[/dim]",
            default="Victorian London, a fog-bound country manor",
        )

    crime_type = args.crime_type
    if not crime_type:
        choices = ["murder", "theft", "forgery", "disappearance", "sabotage", "identity theft", "any"]
        if HAS_RICH:
            _print("\n[cyan]Crime type:[/cyan]")
            for i, c in enumerate(choices, 1):
                _print(f"  [dim]{i}.[/dim] {c}")
            idx = _ask_int("Choose", default=7) - 1
            crime_type = choices[min(max(idx, 0), len(choices) - 1)]
        else:
            crime_type = _ask("Crime type (murder/theft/forgery/disappearance/sabotage/any)", default="any")

    num_players = args.num_players
    if not num_players:
        num_players = _ask_int("[cyan]Number of players[/cyan]", default=4)

    theme = args.theme or ""
    if not theme and not getattr(args, "no_theme", False):
        theme = _ask(
            "[cyan]Theme or twist[/cyan] [dim](optional — leave blank)[/dim]",
            default="",
        )

    max_per_source = getattr(args, "max_per_source", 2)

    # ── Show config ───────────────────────────────────────────────────
    _print("")
    if HAS_RICH:
        t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        t.add_column("K", style="dim")
        t.add_column("V", style="bold white")
        t.add_row("Setting", setting)
        t.add_row("Crime type", crime_type)
        t.add_row("Players", str(num_players))
        if theme:
            t.add_row("Theme / twist", theme)
        t.add_row("Max parts per source", str(max_per_source))
        console.print(Panel(t, title="[yellow]Generation Config[/yellow]", border_style="yellow"))
    else:
        print(f"  Setting      : {setting}")
        print(f"  Crime type   : {crime_type}")
        print(f"  Players      : {num_players}")
        if theme:
            print(f"  Theme        : {theme}")
        print(f"  Max/source   : {max_per_source}")

    if not getattr(args, "yes", False):
        if not _confirm("\n[cyan]Generate?[/cyan]", default=True):
            _print("[dim]Cancelled.[/dim]")
            return

    # ── Load registry ─────────────────────────────────────────────────
    with _spinner("Loading part registry..."):
        registry = _load_registry(args.db_dir)

    stats = registry.stats()
    _print(
        f"[dim]Registry: {stats['total_parts']} parts from "
        f"{len(stats['sources'])} sources "
        f"({', '.join(stats['sources'])})[/dim]"
    )

    # ── Sample parts ──────────────────────────────────────────────────
    from part_registry import PART_TYPE_NAMES
    from coherence_validator import check_parts, check_mystery, rich_panels

    with _spinner("Sampling parts (diversity-constrained)..."):
        selected_parts, recipe = registry.sample_for_generation(
            part_types=PART_TYPE_NAMES,
            target_setting=setting,
            max_per_source=max_per_source,
        )

    # ── Pre-generation coherence check (free — no API call) ───────────
    parts_report = check_parts(selected_parts)
    if parts_report.part_issues:
        if HAS_RICH:
            for content, title, border in rich_panels(parts_report):
                console.print(Panel(content, title=title, border_style=border))
        else:
            _print(parts_report.format_text("PRE-GENERATION PART CHECK"))

        # Attempt targeted re-samples for blocking part issues
        blocking_types = [
            i.code.split(".")[-1]          # e.g. "parts.missing.evidence_type" → "evidence_type"
            for i in parts_report.part_issues
            if i.severity == "blocking" and i.code.startswith("parts.missing.")
        ]
        if blocking_types:
            _print(f"\n[yellow]Re-sampling missing part types: {blocking_types}[/yellow]")
            extra, extra_recipe = registry.sample_for_generation(
                part_types=blocking_types,
                target_setting=setting,
                max_per_source=max_per_source,
            )
            # Merge: replace slots of matching part_type
            existing_by_type = {p.part_type: p for p in selected_parts}
            for p in extra:
                existing_by_type[p.part_type] = p
            selected_parts = list(existing_by_type.values())
            # Re-run to confirm fix
            parts_report2 = check_parts(selected_parts)
            if parts_report2.blocking_count == 0:
                _print("[green]Re-sample resolved blocking part issues.[/green]")
            else:
                _print("[red]Some part issues remain after re-sample; proceeding anyway.[/red]")
    else:
        _print("[dim]Pre-generation part check: OK[/dim]")

    # ── Show selected parts ───────────────────────────────────────────
    if HAS_RICH:
        t = Table(
            "Label", "Part Type", "Source", "Content Preview", "Compat Tags",
            box=box.SIMPLE_HEAD,
            header_style="bold cyan",
            show_lines=False,
        )
        for p in selected_parts:
            preview = p.content[:70] + "…" if len(p.content) > 70 else p.content
            tags = ", ".join(p.setting_tags[:2])
            t.add_row(
                f"[bold yellow]{p.label()}[/bold yellow]",
                f"[dim]{p.part_type}[/dim]",
                f"[cyan]{p.source_id}[/cyan]",
                preview,
                f"[green]{tags}[/green]",
            )
        console.print(Panel(t, title="[cyan]Selected Parts[/cyan]", border_style="cyan"))
    else:
        print("\nSelected Parts:")
        for p in selected_parts:
            print(f"  {p.label():8}  [{p.part_type}]  {p.content[:60]}")

    _print(f"\n[bold]Recipe:[/bold] [yellow]{recipe.format()}[/yellow]")

    # ── Generate mystery ──────────────────────────────────────────────
    demo_mode = getattr(args, "demo", False) or not os.environ.get("ANTHROPIC_API_KEY")
    if demo_mode:
        _print("\n[dim]Demo mode — no Claude API call[/dim]")
        mystery = _demo_mystery(setting, crime_type, num_players, selected_parts, recipe)
    else:
        with _spinner("Generating mystery with Claude..."):
            mystery = _generate_with_claude(
                setting, crime_type, num_players, theme, selected_parts, recipe
            )

    if not mystery:
        _print("[red]Generation failed.[/red]")
        return

    # ── Post-generation coherence check ──────────────────────────────
    mystery_report = check_mystery(mystery)
    if HAS_RICH:
        for content, title, border in rich_panels(mystery_report):
            console.print(Panel(content, title=title, border_style=border))
    else:
        _print(mystery_report.format_text("POST-GENERATION COHERENCE CHECK"))

    if not mystery_report.passed:
        _print(
            "[red]Mystery has BLOCKING coherence issues.[/red] "
            "Review the report above. The mystery has been saved for inspection "
            "but should not be used in gameplay until fixed."
        )
    # Attach coherence report to saved output for traceability
    mystery["_coherence"] = {
        "passed": mystery_report.passed,
        "blocking": mystery_report.blocking_count,
        "warnings": mystery_report.warning_count,
        "witness_gaps": [
            {"name": g.character_name, "role": g.role, "missing": g.missing}
            for g in mystery_report.witness_gaps
        ],
    }

    recipe.generated_title = mystery.get("title", "Untitled")
    _display_mystery(mystery, recipe)
    _save_mystery(mystery, recipe, args.db_dir)


# ============================================================================
# COMMAND: solve  (MysterySolver mode)
# ============================================================================

def cmd_solve(args):
    """
    Analyze an existing mystery scenario and identify the likely solution.

    Emulates the MysterySolver HuggingFace Space interface in the terminal:
    — input: free-text mystery description (suspects, clues, setting)
    — output: structured analysis (culprit, reasoning, red herrings, next steps)
    """
    _banner()
    _print("\n[bold magenta]🔎  MYSTERY SOLVER[/bold magenta]")
    _print("[dim]Describe a mystery and receive a structured deduction analysis.[/dim]\n")

    description = getattr(args, "description", None) or ""
    if not description:
        if HAS_RICH:
            _print("[cyan]Describe your mystery scenario:[/cyan]")
            _print("[dim]Include: the crime, setting, suspects, any known clues.[/dim]")
            _print("[dim]Press Enter on a blank line when done.[/dim]\n")
            lines = []
            while True:
                line = Prompt.ask("[dim]>[/dim]", default="")
                if not line and lines:
                    break
                if line:
                    lines.append(line)
            description = "\n".join(lines)
        else:
            print("Describe your mystery (blank line to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines:
                    break
                if line:
                    lines.append(line)
            description = "\n".join(lines)

    if not description.strip():
        _print("[red]No description provided.[/red]")
        return

    demo_mode = getattr(args, "demo", False) or not os.environ.get("ANTHROPIC_API_KEY")
    if demo_mode:
        _print("[dim]Demo mode — no Claude API call[/dim]")
        analysis = _demo_solve(description)
    else:
        with _spinner("Analyzing mystery..."):
            analysis = _solve_with_claude(description)

    _display_solution(analysis)


# ============================================================================
# COMMAND: list
# ============================================================================

def cmd_list(args):
    """List generated and canonical mysteries in the database."""
    _banner()
    db_dir = Path(args.db_dir)
    _print("\n[bold]Mystery Database[/bold]\n")

    # ── Canonical test corpus ─────────────────────────────────────────
    try:
        from test_mysteries import TEST_MYSTERIES
        if HAS_RICH:
            t = Table(
                "ID", "Title", "Crime", "Setting", "Period",
                box=box.SIMPLE_HEAD, header_style="bold cyan",
            )
            for mid, m in TEST_MYSTERIES.items():
                t.add_row(
                    f"[bold]{mid}[/bold]",
                    m["title"],
                    m.get("crime_type", ""),
                    m.get("setting_location", "")[:35],
                    m.get("setting_time_period", ""),
                )
            console.print(Panel(t, title="[yellow]Canonical Test Corpus (A–F)[/yellow]", border_style="yellow"))
        else:
            print("Canonical Test Corpus:")
            print("-" * 62)
            for mid, m in TEST_MYSTERIES.items():
                print(f"  [{mid}] {m['title']:<40}  {m.get('crime_type','')}")
    except ImportError:
        pass

    # ── Generated mysteries ───────────────────────────────────────────
    gen_dir = db_dir / "generated"
    if gen_dir.exists():
        files = sorted(gen_dir.glob("*.json"))
        if files:
            if HAS_RICH:
                t = Table(
                    "Title", "Setting", "Crime", "Players", "Recipe",
                    box=box.SIMPLE_HEAD, header_style="bold cyan",
                )
                for f in files[:30]:
                    try:
                        with open(f) as fp:
                            data = json.load(fp)
                        title = data.get("title", f.stem)[:38]
                        loc = str(data.get("setting", {}).get("location", ""))[:28]
                        crime = str(data.get("crime", {}).get("type", ""))[:14]
                        players = str(data.get("_meta", {}).get("num_players", "?"))
                        recipe = data.get("_provenance", {}).get("recipe", "—")[:38]
                        t.add_row(title, loc, crime, players, f"[dim]{recipe}[/dim]")
                    except Exception:
                        pass
                console.print(
                    Panel(t, title=f"[yellow]Generated ({len(files)})[/yellow]", border_style="yellow")
                )
            else:
                print(f"\nGenerated Mysteries ({len(files)}):")
                print("-" * 62)
                for f in files[:20]:
                    try:
                        with open(f) as fp:
                            data = json.load(fp)
                        recipe = data.get("_provenance", {}).get("recipe", "")
                        print(f"  {data.get('title','?')[:40]:<42} {recipe}")
                    except Exception:
                        pass
        else:
            _print("[dim]No generated mysteries yet. Run: python cli.py generate[/dim]")
    else:
        _print("[dim]No generated mysteries yet. Run: python cli.py generate[/dim]")


# ============================================================================
# COMMAND: registry
# ============================================================================

def cmd_registry(args):
    """Show part registry statistics and source diversity."""
    _banner()
    _print("\n[bold]Part Registry[/bold]\n")

    with _spinner("Loading registry..."):
        registry = _load_registry(args.db_dir)

    stats = registry.stats()
    _print(f"Total parts : [bold cyan]{stats['total_parts']}[/bold cyan]")
    _print(f"Sources     : [bold cyan]{len(stats['sources'])}[/bold cyan]  ({', '.join(stats['sources'])})\n")

    from part_registry import PART_TYPE_NAMES
    if HAS_RICH:
        t = Table("Part Type", "Index", "Count", box=box.SIMPLE_HEAD, header_style="bold")
        for idx, ptype in enumerate(PART_TYPE_NAMES, 1):
            count = stats["by_type"].get(ptype, 0)
            t.add_row(ptype, str(idx), str(count))
        console.print(t)

        # Per-source breakdown
        _print("\n[bold]Parts per source:[/bold]")
        t2 = Table("Source", "Count", "Title / ID", box=box.SIMPLE_HEAD, header_style="bold")
        for src in stats["sources"]:
            count = stats["by_source"].get(src, 0)
            # Find a title for this source
            sample = next((p for p in registry.parts if p.source_id == src), None)
            title = sample.source_title if sample else ""
            t2.add_row(f"[yellow]{src}[/yellow]", str(count), f"[dim]{title[:50]}[/dim]")
        console.print(t2)
    else:
        for idx, ptype in enumerate(PART_TYPE_NAMES, 1):
            count = stats["by_type"].get(ptype, 0)
            print(f"  [{idx}] {ptype:<25}  {count} parts")
        print()
        for src in stats["sources"]:
            count = stats["by_source"].get(src, 0)
            print(f"  {src}: {count} parts")


# ============================================================================
# COMMAND: extract
# ============================================================================

def cmd_extract(args):
    """Delegate to run_corpus_pipeline.py."""
    cmd = [sys.executable, "run_corpus_pipeline.py", "--protocol", args.protocol]
    if getattr(args, "start", None):
        cmd += ["--start", str(args.start)]
    if getattr(args, "end", None):
        cmd += ["--end", str(args.end)]
    if getattr(args, "dry_run", False):
        cmd += ["--dry-run"]
    import subprocess
    subprocess.run(cmd)


# ============================================================================
# DISPLAY: mystery output
# ============================================================================

def _display_mystery(mystery: dict, recipe):
    _print("")
    _rule(f"[bold cyan]{mystery.get('title', 'Mystery')}[/bold cyan]")

    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    solution = mystery.get("solution", {})
    gameplay = mystery.get("gameplay_notes", {})

    # Setting panel
    _panel(
        f"[bold]{setting.get('location', '')}[/bold]"
        f"  ·  {setting.get('time_period', '')}  ·  {setting.get('environment', '')}\n\n"
        f"{setting.get('description', '')}",
        title="[yellow]Setting[/yellow]", border="yellow",
    )

    # Crime panel
    _panel(
        f"[bold red]{crime.get('type', '').upper()}[/bold red]\n\n"
        f"{crime.get('what_happened', '')}\n\n"
        f"[dim]When:[/dim] {crime.get('when', '')}   "
        f"[dim]Discovery:[/dim] {crime.get('initial_discovery', '')}",
        title="[red]The Crime[/red]", border="red",
    )

    # Characters
    chars = mystery.get("characters", [])
    if chars and HAS_RICH:
        t = Table(
            "Name", "Role", "Occupation", "Motive", "Alibi",
            box=box.SIMPLE_HEAD, header_style="bold",
        )
        ROLE_STYLE = {"victim": "red", "suspect": "yellow", "detective": "cyan", "witness": "dim"}
        for c in chars:
            role = c.get("role", "")
            rs = ROLE_STYLE.get(role, "white")
            t.add_row(
                f"[bold]{c.get('name', '')}[/bold]",
                f"[{rs}]{role}[/{rs}]",
                c.get("occupation", ""),
                c.get("motive", "—"),
                c.get("alibi", "—"),
            )
        console.print(Panel(t, title="[yellow]Characters[/yellow]", border_style="yellow"))
    elif chars:
        print("\nCharacters:")
        for c in chars:
            print(f"  {c.get('name','?'):20} [{c.get('role','?')}]  {c.get('motive','')}")

    # Evidence
    evidence = mystery.get("evidence", [])
    if evidence and HAS_RICH:
        t = Table(
            "ID", "Name", "Type", "Relevance", "Description",
            box=box.SIMPLE_HEAD, header_style="bold",
        )
        REL_STYLE = {"critical": "bold red", "supporting": "yellow", "red_herring": "dim"}
        for e in evidence:
            rel = e.get("relevance", "")
            rs = REL_STYLE.get(rel, "white")
            t.add_row(
                e.get("id", ""),
                e.get("name", ""),
                e.get("type", ""),
                f"[{rs}]{rel}[/{rs}]",
                e.get("description", "")[:55],
            )
        console.print(Panel(t, title="[green]Evidence[/green]", border_style="green"))
    elif evidence:
        print("\nEvidence:")
        for e in evidence:
            print(f"  [{e.get('id','?')}] {e.get('name','?'):25} [{e.get('relevance','?')}]")

    # Gameplay summary
    meta = mystery.get("_meta", {})
    _panel(
        f"[dim]Difficulty:[/dim] [bold]{gameplay.get('difficulty', '?')}[/bold]   "
        f"[dim]Playtime:[/dim] {gameplay.get('estimated_playtime', '?')}   "
        f"[dim]Players:[/dim] {meta.get('num_players', '?')}\n\n"
        + ("\n".join(f"• {t}" for t in gameplay.get("key_twists", []))),
        title="[blue]Gameplay[/blue]", border="blue",
    )

    # Provenance recipe
    _panel(
        f"[bold yellow]{recipe.format()}[/bold yellow]\n\n"
        f"[dim]Setting:[/dim] {recipe.target_setting}\n"
        f"[dim]Parts used:[/dim] {len(recipe.slots)}   "
        f"[dim]Max per source:[/dim] enforced at generation time\n\n"
        "[dim]This recipe is unique — re-running will produce a different combination.[/dim]",
        title="[cyan]Provenance Recipe[/cyan]", border="cyan",
    )

    # Reveal solution on request (only in interactive terminal)
    if sys.stdin.isatty() and _confirm("\n[dim]Reveal solution? (spoilers)[/dim]", default=False):
        _panel(
            f"[bold red]Culprit:[/bold red] {solution.get('culprit', '?')}\n"
            f"[bold]Method:[/bold] {solution.get('method', '?')}\n"
            f"[bold]Motive:[/bold] {solution.get('motive', '?')}\n"
            f"[bold]Key evidence:[/bold] {', '.join(solution.get('key_evidence', []))}\n\n"
            f"[dim]{solution.get('how_to_deduce', '')}[/dim]",
            title="[red]⚠  SOLUTION — SPOILERS[/red]", border="red",
        )


# ============================================================================
# DISPLAY: solution analysis
# ============================================================================

def _display_solution(analysis: dict):
    _print("")
    confidence = analysis.get("confidence", "medium")
    CONF_STYLE = {"high": "green", "medium": "yellow", "low": "red"}
    cs = CONF_STYLE.get(confidence, "white")

    _panel(
        f"[bold]{analysis.get('most_likely_culprit', '?')}[/bold]\n"
        f"Confidence: [{cs}]{confidence.upper()}[/{cs}]\n\n"
        f"[dim]Method:[/dim] {analysis.get('method', '?')}\n"
        f"[dim]Motive:[/dim] {analysis.get('motive', '?')}",
        title="[bold red]Most Likely Culprit[/bold red]", border="red",
    )

    _panel(analysis.get("reasoning", ""), title="[yellow]Deductive Reasoning[/yellow]", border="yellow")

    red_herrings = analysis.get("red_herrings", [])
    if red_herrings:
        _panel(
            "\n".join(f"• {r}" for r in red_herrings),
            title="[dim]Red Herrings Identified[/dim]", border="dim",
        )

    alt = analysis.get("alternative_suspects", [])
    if alt and HAS_RICH:
        t = Table("Suspect", "Why Suspected", "Why Cleared", box=box.SIMPLE_HEAD, header_style="bold")
        for s in alt:
            t.add_row(s.get("name", ""), s.get("why_suspected", ""), s.get("why_cleared", ""))
        console.print(Panel(t, title="[dim]Alternative Suspects[/dim]", border_style="dim"))

    next_steps = analysis.get("what_to_investigate_next", [])
    if next_steps:
        _panel(
            "\n".join(f"→ {s}" for s in next_steps),
            title="[cyan]Next Investigative Steps[/cyan]", border="cyan",
        )


# ============================================================================
# CLAUDE INTEGRATION
# ============================================================================

def _generate_with_claude(
    setting: str,
    crime_type: str,
    num_players: int,
    theme: str,
    selected_parts,
    recipe,
) -> dict:
    import anthropic

    parts_block = "\n".join(
        f"  [{p.label()} — {p.part_type}]: {p.content}"
        for p in selected_parts
    )

    crime_line = f"Crime type: {crime_type}" if crime_type != "any" else "Choose the most fitting crime type for this setting."
    theme_line = f"Theme / twist: {theme}" if theme else ""

    prompt = f"""\
You are generating a mystery scenario for a social deduction game with {num_players} players.

SETTING: {setting}
{crime_line}
{theme_line}

The following atomized parts have been selected from existing mystery literature using
part-tracked RAG (recipe: {recipe.format()}). Adapt them to the target setting — do not
copy them verbatim.

SELECTED PARTS:
{parts_block}

QUALITY REQUIREMENTS — every generated mystery MUST satisfy these or it fails validation:

SETTING:
  - description must explicitly explain why suspects cannot simply leave (isolation mechanic).

CHARACTERS (include 1 victim, 3–4 suspects, optionally 1–2 witnesses):
  - alibi: SPECIFIC — state where the person was, with whom or doing what. Never "—" or vague.
    Good: "Was supervising the night shift in the boiler room with two apprentices until dawn."
    Bad: "Was elsewhere." or "—"
  - secret: CONCRETE FACT (≥ 2 sentences) that anchors interrogation questions like
    "Why were you near the victim?" or "Why didn't you report what you saw?"
    Good: "Had borrowed money from the victim six months ago and had not repaid it; was seen
           arguing with them the evening before in the garden."
    Bad: "Has a dark past."
  - motive (suspects): specific stake — financial, relational, reputational, or political.
    Never "—" for suspects.
  - occupation: always present; must logically place the character in the closed world.

EVIDENCE (include at least 6 items total):
  - At least 2 items with type "physical" — objects or traces found at the scene.
  - At least 1 item with relevance "red_herring" and type "physical" or "documentary"
    so players find a misleading clue during scene investigation, not only from dialogue.
  - At least 2 items with relevance "critical".
  - description: ≥ 2 sentences; state what the item is, where it was found, and what it
    initially suggests to an investigator.

SOLUTION:
  - key_evidence must list at least 2 evidence IDs that, together, prove the culprit's guilt.
  - how_to_deduce: step-by-step logic chain (3+ steps), not a single sentence.

Generate a complete mystery JSON with this exact structure:
{{
  "title": "string",
  "setting": {{
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentence atmospheric description including why suspects cannot leave"
  }},
  "crime": {{
    "type": "string",
    "what_happened": "string",
    "when": "string",
    "initial_discovery": "string"
  }},
  "characters": [
    {{
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string (explains their presence in the closed world)",
      "motive": "string — specific stake; never — for suspects",
      "alibi": "string — specific location, activity, and corroborating person/detail",
      "secret": "string — concrete 2-sentence fact anchoring why-were-you-there questions"
    }}
  ],
  "evidence": [
    {{
      "id": "E1",
      "name": "string",
      "description": "string",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring"
    }}
  ],
  "solution": {{
    "culprit": "string",
    "method": "string",
    "motive": "string",
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "step-by-step reasoning"
  }},
  "gameplay_notes": {{
    "difficulty": "EASY | MEDIUM | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  }}
}}

Return only valid JSON. No commentary outside the JSON block."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    mystery = json.loads(text)
    mystery["_meta"] = {"num_players": num_players, "setting_input": setting}
    mystery["_provenance"] = recipe.to_dict()
    return mystery


def _solve_with_claude(description: str) -> dict:
    import anthropic

    prompt = f"""\
Analyze this mystery scenario and identify the most likely solution.

MYSTERY DESCRIPTION:
{description}

Return a structured JSON analysis:
{{
  "most_likely_culprit": "name or 'Unknown'",
  "confidence": "high | medium | low",
  "method": "how the crime was committed",
  "motive": "why they did it",
  "key_evidence": ["list of clues pointing to the culprit"],
  "red_herrings": ["list of misleading elements to discard"],
  "alternative_suspects": [
    {{
      "name": "string",
      "why_suspected": "string",
      "why_cleared": "string"
    }}
  ],
  "reasoning": "step-by-step deductive reasoning",
  "what_to_investigate_next": ["questions that remain open"]
}}

Return only valid JSON."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)


# ============================================================================
# DEMO OUTPUTS (no API required)
# ============================================================================

def _demo_mystery(setting, crime_type, num_players, selected_parts, recipe) -> dict:
    loc = setting.split(",")[0].strip()
    effective_crime = crime_type if crime_type not in ("any", "") else "murder"

    return {
        "title": f"The {effective_crime.title()} at {loc}",
        "setting": {
            "location": setting,
            "time_period": "period inferred from setting",
            "environment": "closed circle of suspects",
            "description": (
                f"The air in {loc} is thick with suspicion. A small, isolated group "
                f"finds itself bound together by circumstance — and by the {effective_crime} "
                f"that none of them will admit to witnessing."
            ),
        },
        "crime": {
            "type": effective_crime,
            "what_happened": "A body was discovered in the locked study at midnight.",
            "when": "Between 11 PM and midnight",
            "initial_discovery": "The housekeeper raised the alarm when she found the door sealed from within.",
        },
        "characters": [
            {"name": "Lady Hartwell", "role": "victim", "occupation": "Wealthy patron",
             "motive": "—", "alibi": "—", "secret": "Recently altered her will"},
            {"name": "Dr. Pemberton", "role": "suspect", "occupation": "Physician",
             "motive": "Stands to inherit under the old will", "alibi": "Claims to be in the library",
             "secret": "Deeply in debt, creditors closing in"},
            {"name": "Miss Crane", "role": "suspect", "occupation": "Personal secretary",
             "motive": "Blackmail — knows about the forgery", "alibi": "Unverified",
             "secret": "Was the victim's confidante and knows too much"},
            {"name": "Inspector Vane", "role": "detective", "occupation": "Police",
             "motive": "—", "alibi": "—", "secret": "—"},
        ],
        "evidence": [
            {"id": "E1", "name": "Stopped pocket watch", "description": "Found on the victim, stopped at 11:47 PM",
             "type": "physical", "relevance": "critical"},
            {"id": "E2", "name": "Torn letter", "description": "References a sum large enough to ruin a man",
             "type": "documentary", "relevance": "critical"},
            {"id": "E3", "name": "Muddy boots by the back door", "description": "No one admits to going outside",
             "type": "physical", "relevance": "supporting"},
            {"id": "E4", "name": "Empty medicine vial", "description": "An unusual sedative not prescribed to the victim",
             "type": "physical", "relevance": "red_herring"},
        ],
        "solution": {
            "culprit": "Dr. Pemberton",
            "method": "Poison administered in the evening tea, timed to allow an apparent alibi",
            "motive": "Stood to inherit under the old will; new will cuts him out entirely",
            "key_evidence": ["E1", "E2"],
            "how_to_deduce": (
                "The stopped watch (E1) fixes time of death at 11:47 PM, contradicting Pemberton's "
                "alibi that he was in the library until midnight. The torn letter (E2) establishes his "
                "desperate motive. The medicine vial (E4) is a red herring — it belonged to Miss Crane legitimately."
            ),
        },
        "gameplay_notes": {
            "difficulty": "MEDIUM",
            "estimated_playtime": "45–60 minutes",
            "key_twists": [
                "The will was changed three days before the murder",
                "Miss Crane is a witness, not a suspect — she saw Pemberton leave the library early",
            ],
        },
        "_meta": {"num_players": num_players, "setting_input": setting, "demo": True},
        "_provenance": recipe.to_dict(),
    }


def _demo_solve(description: str) -> dict:
    return {
        "most_likely_culprit": "The person with both motive and unverified alibi",
        "confidence": "medium",
        "method": "Staged accident or poison — method conceals premeditation",
        "motive": "Inheritance, blackmail silencing, or rivalry",
        "key_evidence": [
            "Unverified alibi at critical time window",
            "Financial motive established by documents",
            "Physical access to the crime scene",
        ],
        "red_herrings": [
            "The suspicious stranger seen near the property",
            "The unlocked window (coincidental, not used)",
        ],
        "alternative_suspects": [
            {
                "name": "Secondary suspect",
                "why_suspected": "Present at scene, known grievance with victim",
                "why_cleared": "Corroborated alibi from independent witness",
            }
        ],
        "reasoning": (
            "Working through means, motive, and opportunity: the primary suspect had the clearest "
            "financial motive, was present during the critical window, and their alibi collapses "
            "under scrutiny. The secondary suspect looked guilty by association, but that is precisely "
            "what the actual culprit intended — a classic frame constructed from circumstantial detail.\n\n"
            "[Demo mode — run with ANTHROPIC_API_KEY set for Claude analysis]"
        ),
        "what_to_investigate_next": [
            "Verify the exact timeline with independent witnesses",
            "Check financial records for the motive chain",
            "Re-examine physical evidence for traces linking to primary suspect",
        ],
    }


# ============================================================================
# SAVE
# ============================================================================

def _save_mystery(mystery: dict, recipe, db_dir: str):
    out_dir = Path(db_dir) / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    title = mystery.get("title", "mystery").lower()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:40]
    filename = f"{safe}_{int(time.time())}.json"
    filepath = out_dir / filename
    with open(filepath, "w") as f:
        json.dump(mystery, f, indent=2)
    _print(f"\n[dim]Saved → {filepath}[/dim]")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="mystery",
        description="Choose Your Mystery — CLI for mystery generation and analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python cli.py generate --demo
  python cli.py generate --setting "Ancient Athens, agora" --crime-type murder
  python cli.py solve
  python cli.py list
  python cli.py registry
  python cli.py extract --protocol P1P2 --dry-run
""",
    )
    parser.add_argument("--db-dir", default="./mystery_database", metavar="DIR",
                        help="Mystery database directory (default: ./mystery_database)")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── generate ──────────────────────────────────────────────────────
    g = sub.add_parser("generate", aliases=["gen", "g"], help="Generate a new mystery")
    g.add_argument("--setting", "-s", metavar="TEXT",
                   help="Setting description (e.g. 'Ancient Athens, agora, 400 BC')")
    g.add_argument("--crime-type", "-c", metavar="TYPE",
                   help="Crime type: murder / theft / forgery / disappearance / sabotage / any")
    g.add_argument("--num-players", "-n", type=int, metavar="N",
                   help="Number of players (default: 4)")
    g.add_argument("--theme", "-t", metavar="TEXT",
                   help="Optional theme or twist")
    g.add_argument("--max-per-source", type=int, default=2, metavar="N",
                   help="Diversity constraint: max parts from one source (default: 2)")
    g.add_argument("--demo", action="store_true",
                   help="Demo mode — no Claude API call required")
    g.add_argument("--yes", "-y", action="store_true",
                   help="Skip confirmation prompt")
    g.add_argument("--no-theme", action="store_true",
                   help="Skip the theme prompt")
    g.set_defaults(func=cmd_generate)

    # ── solve ─────────────────────────────────────────────────────────
    s = sub.add_parser("solve", aliases=["s"], help="Analyze and solve a mystery (MysterySolver mode)")
    s.add_argument("description", nargs="?", metavar="TEXT",
                   help="Mystery description (or omit for interactive input)")
    s.add_argument("--demo", action="store_true",
                   help="Demo mode — no Claude API call required")
    s.set_defaults(func=cmd_solve)

    # ── list ──────────────────────────────────────────────────────────
    l = sub.add_parser("list", aliases=["ls"], help="Browse the mystery database")
    l.set_defaults(func=cmd_list)

    # ── registry ──────────────────────────────────────────────────────
    r = sub.add_parser("registry", aliases=["reg"], help="Inspect the part registry")
    r.set_defaults(func=cmd_registry)

    # ── extract ───────────────────────────────────────────────────────
    e = sub.add_parser("extract", help="Run corpus extraction pipeline")
    e.add_argument("--protocol", default="P1P2",
                   help="Extraction depth: P1 / P2 / P1P2 / P1P2P3 (default: P1P2)")
    e.add_argument("--start", type=int, default=0, metavar="N")
    e.add_argument("--end", type=int, metavar="N")
    e.add_argument("--dry-run", action="store_true")
    e.set_defaults(func=cmd_extract)

    args = parser.parse_args()

    if not args.command:
        _banner()
        _print("")
        parser.print_help()
        _print("")
        _print("[bold cyan]Quick start (no API key needed):[/bold cyan]")
        _print("  python cli.py generate --demo")
        _print("  python cli.py solve --demo")
        _print("  python cli.py list")
        _print("  python cli.py registry")
        return

    args.func(args)


if __name__ == "__main__":
    main()
