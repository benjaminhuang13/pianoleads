"""
main.py
───────
CLI entry point for Piano Lead Finder.

Commands:
  scrape   — run scrapers for a territory
  enrich   — run WHOIS + scoring on stored leads
  export   — export leads to CSV
  stats    — show lead database summary
  review   — interactively review flagged duplicate leads
  mark     — mark a lead as taken / update status

Usage examples:
  python main.py scrape --source google_maps --territory nyc_metro
  python main.py scrape --source google_maps --territory all
  python main.py enrich
  python main.py export --output output/leads_nyc.csv --territory nyc_metro
  python main.py stats
  python main.py review
  python main.py mark <lead-id> --status taken --rep "Sarah"
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from config.settings import LEADS_DB_PATH
from config.territories import TERRITORY_CONFIGS, get_territory_config
from processors.deduplicator import Deduplicator
from processors.enricher import Enricher
from processors.normalizer import Normalizer
from storage.exporter import export_to_csv
from storage.schema import LeadStatus, SourceType, Territory
from storage.store import LeadStore
from utils.logger import setup_logging

console = Console()


# ─────────────────────────────────────────────
# Scraper registry — add new scrapers here
# ─────────────────────────────────────────────

def get_scraper(source: str):
    """Return the scraper instance for a given source name."""
    if source == "google_maps":
        from scrapers.google_maps import GoogleMapsScraper
        return GoogleMapsScraper()
    if source == "domain_crawl":
        from scrapers.domain_crawler import DomainCrawler
        return DomainCrawler()
    raise ValueError(f"Unknown source: '{source}'. Available: google_maps, domain_crawl")


AVAILABLE_SOURCES = ["google_maps", "domain_crawl"]
AVAILABLE_TERRITORIES = [t.value for t in Territory] + ["all"]


# ─────────────────────────────────────────────
# Command handlers
# ─────────────────────────────────────────────

def cmd_scrape(args, store: LeadStore) -> None:
    """Run scrapers and save results."""
    normalizer = Normalizer()
    deduplicator = Deduplicator(store)

    # Resolve territories
    if args.territory == "all":
        territories = list(Territory)
    else:
        try:
            territories = [Territory(args.territory)]
        except ValueError:
            console.print(f"[red]Unknown territory: {args.territory}[/red]")
            console.print(f"Available: {AVAILABLE_TERRITORIES}")
            sys.exit(1)

    # Resolve scraper
    try:
        scraper = get_scraper(args.source)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    total_new = 0
    total_updated = 0

    for territory in territories:
        config = get_territory_config(territory)
        console.rule(f"[bold]{config.name}[/bold]")

        # 1. Scrape
        console.print(f"[cyan]Scraping {args.source}...[/cyan]")
        raw_leads = scraper.run(territory, config)
        console.print(f"  Scraped [bold]{len(raw_leads)}[/bold] raw leads")

        # 2. Normalize
        leads = normalizer.normalize_many(raw_leads)
        console.print(f"  Normalized [bold]{len(leads)}[/bold] valid leads")

        # 3. Deduplicate + save
        new_count = 0
        updated_count = 0
        flagged_count = 0

        for lead in leads:
            lead_to_save, is_new = deduplicator.process(lead)
            store.save_lead(lead_to_save)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
            if lead_to_save.duplicate_of:
                flagged_count += 1

        console.print(
            f"  Saved: [green]{new_count} new[/green], "
            f"[yellow]{updated_count} updated[/yellow], "
            f"[magenta]{flagged_count} flagged for review[/magenta]"
        )
        total_new += new_count
        total_updated += updated_count

    console.rule()
    console.print(
        f"[bold green]Done.[/bold green] "
        f"{total_new} new leads, {total_updated} updated. "
        f"Run [cyan]python main.py enrich[/cyan] to score leads."
    )


def cmd_enrich(args, store: LeadStore) -> None:
    """Run WHOIS enrichment and confidence scoring."""
    enricher = Enricher(store)
    enriched = enricher.enrich_all(force=getattr(args, "force", False))
    console.print(f"[green]Enriched {enriched} leads.[/green]")


def cmd_export(args, store: LeadStore) -> None:
    """Export leads to CSV."""
    # Build filter kwargs
    filter_kwargs = {}
    if getattr(args, "territory", None) and args.territory != "all":
        filter_kwargs["territory"] = Territory(args.territory)
    if getattr(args, "source", None):
        filter_kwargs["source"] = SourceType(args.source)
    if getattr(args, "status", None):
        filter_kwargs["status"] = LeadStatus(args.status)
    if getattr(args, "min_rating", None):
        filter_kwargs["min_rating"] = float(args.min_rating)
    if getattr(args, "min_reviews", None):
        filter_kwargs["min_reviews"] = int(args.min_reviews)

    sort_by = getattr(args, "sort_by", "found_at") or "found_at"
    filter_kwargs["sort_by"] = sort_by

    leads = store.filter(**filter_kwargs)
    output = getattr(args, "output", None) or "output/leads_export.csv"
    include_taken = getattr(args, "include_taken", False)

    count = export_to_csv(leads, output, include_taken=include_taken)
    console.print(f"[green]Exported {count} leads to {output}[/green]")


def cmd_stats(args, store: LeadStore) -> None:
    """Print lead database summary."""
    stats = store.stats()
    total = stats.get("total", 0)

    if total == 0:
        console.print("[yellow]No leads in database yet. Run a scrape first.[/yellow]")
        return

    console.print(f"\n[bold]Piano Lead Database — {total} total leads[/bold]\n")

    # By status
    t = Table("Status", "Count", box=box.SIMPLE)
    for k, v in sorted(stats.get("by_status", {}).items()):
        t.add_row(k, str(v))
    console.print(t)

    # By territory
    t2 = Table("Territory", "Count", box=box.SIMPLE)
    for k, v in sorted(stats.get("by_territory", {}).items()):
        t2.add_row(k, str(v))
    console.print(t2)

    # By source
    t3 = Table("Source", "Count", box=box.SIMPLE)
    for k, v in sorted(stats.get("by_source", {}).items(), key=lambda x: -x[1]):
        t3.add_row(k, str(v))
    console.print(t3)

    # Contact coverage
    console.print(
        f"Has phone: [green]{stats['with_phone']}[/green]  |  "
        f"Has website: [green]{stats['with_website']}[/green]  |  "
        f"Has email: [green]{stats['with_email']}[/green]  |  "
        f"New: [cyan]{stats['new_leads']}[/cyan]"
    )


def cmd_review(args, store: LeadStore) -> None:
    """Interactively review flagged duplicate leads."""
    deduplicator = Deduplicator(store)
    pending = deduplicator.get_pending_reviews()

    if not pending:
        console.print("[green]No duplicate flags to review.[/green]")
        return

    console.print(f"\n[bold]{len(pending)} leads flagged for duplicate review.[/bold]\n")

    for flagged, candidate in pending:
        console.rule()
        console.print(f"[bold magenta]Flagged lead:[/bold magenta]  {flagged.display_name()} ({flagged.id[:8]})")
        console.print(f"  Phone:   {flagged.phone or '—'}")
        console.print(f"  Website: {flagged.website or '—'}")
        console.print(f"  Source:  {flagged.source.value}")
        console.print(f"  Notes:   {flagged.notes or '—'}")

        if candidate:
            console.print(f"\n[bold yellow]Possible duplicate:[/bold yellow] {candidate.display_name()} ({candidate.id[:8]})")
            console.print(f"  Phone:   {candidate.phone or '—'}")
            console.print(f"  Website: {candidate.website or '—'}")
            console.print(f"  Status:  {candidate.status.value}")

        console.print("\n[bold]Action:[/bold] [M]erge  [D]ismiss  [S]kip", end=" ")
        try:
            choice = input().strip().upper()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Review cancelled.[/yellow]")
            return

        if choice == "M" and candidate:
            merged = deduplicator.merge(candidate, flagged)
            store.save_lead(merged)
            # Remove the flagged duplicate record
            all_leads = store._load_leads()
            all_leads.pop(flagged.id, None)
            store._save_all(all_leads)
            console.print("[green]Merged.[/green]")
        elif choice == "D":
            deduplicator.dismiss_duplicate_flag(flagged.id)
            console.print("[green]Dismissed — lead kept as separate record.[/green]")
        else:
            console.print("[dim]Skipped.[/dim]")


def cmd_mark(args, store: LeadStore) -> None:
    """Mark a lead's status or assign it to a rep."""
    lead_id_prefix = args.lead_id
    # Support partial ID match
    all_leads = store.all_leads()
    matches = [l for l in all_leads if l.id.startswith(lead_id_prefix)]

    if not matches:
        console.print(f"[red]No lead found with ID starting with '{lead_id_prefix}'[/red]")
        sys.exit(1)
    if len(matches) > 1:
        console.print(f"[red]Ambiguous ID — {len(matches)} leads match. Use more characters.[/red]")
        sys.exit(1)

    lead = matches[0]
    changed = False

    if args.status:
        try:
            lead.status = LeadStatus(args.status)
            changed = True
        except ValueError:
            console.print(f"[red]Invalid status: {args.status}[/red]")
            console.print(f"Valid: {[s.value for s in LeadStatus]}")
            sys.exit(1)

    if getattr(args, "rep", None):
        lead.assigned_to = args.rep
        changed = True

    if changed:
        store.save_lead(lead)
        console.print(f"[green]Updated lead {lead.id[:8]}: {lead.display_name()}[/green]")
    else:
        console.print("[yellow]Nothing to update. Use --status or --rep.[/yellow]")


# ─────────────────────────────────────────────
# CLI argument parser
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piano-leads",
        description="🎹 Piano Lead Finder — Lead generation for piano sales reps",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # scrape
    p_scrape = sub.add_parser("scrape", help="Run scrapers to find new leads")
    p_scrape.add_argument("--source", "-s", required=True, choices=AVAILABLE_SOURCES)
    p_scrape.add_argument("--territory", "-t", default="all", choices=AVAILABLE_TERRITORIES)

    # enrich
    p_enrich = sub.add_parser("enrich", help="Run WHOIS and confidence scoring")
    p_enrich.add_argument("--force", action="store_true", help="Re-enrich all leads, not just new ones")

    # export
    p_export = sub.add_parser("export", help="Export leads to CSV")
    p_export.add_argument("--output", "-o", default="output/leads_export.csv")
    p_export.add_argument("--territory", "-t", default="all", choices=AVAILABLE_TERRITORIES)
    p_export.add_argument("--source", "-s", choices=AVAILABLE_SOURCES)
    p_export.add_argument("--status", choices=[s.value for s in LeadStatus])
    p_export.add_argument("--min-rating", type=float)
    p_export.add_argument("--min-reviews", type=int)
    p_export.add_argument(
        "--sort-by",
        default="found_at",
        choices=["found_at", "rating", "review_count", "most_recent_review",
                 "photo_count", "domain_age_days", "confidence_score"],
    )
    p_export.add_argument("--include-taken", action="store_true")

    # stats
    sub.add_parser("stats", help="Show lead database statistics")

    # review
    sub.add_parser("review", help="Review flagged duplicate leads")

    # mark
    p_mark = sub.add_parser("mark", help="Mark a lead's status or assign to a rep")
    p_mark.add_argument("lead_id", help="Lead ID or prefix (first 8 chars)")
    p_mark.add_argument("--status", choices=[s.value for s in LeadStatus])
    p_mark.add_argument("--rep", help="Rep name to assign this lead to")

    return parser


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    store = LeadStore(LEADS_DB_PATH)

    commands = {
        "scrape":  cmd_scrape,
        "enrich":  cmd_enrich,
        "export":  cmd_export,
        "stats":   cmd_stats,
        "review":  cmd_review,
        "mark":    cmd_mark,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args, store)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
