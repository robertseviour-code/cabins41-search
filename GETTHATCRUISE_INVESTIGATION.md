# Get That Cruise extraction investigation — 12 November 2026

Source: https://www.getthatcruise.co.uk/cruises/solo-fares

- Solo-fares landing page reports **439** sailings but explicitly says **"First 60 shown here"**. Thus scraping the landing page cannot recover the whole catalogue.
- The catalogue landing page displays **solo** and **per-person sharing** prices together on many of those first 60 cards; some cards lack a sharing price. Keep such cards for review, with supplement unknown.
- The finder link is https://www.getthatcruise.co.uk/cruises?chips=solo ; its HTML appears to be a JavaScript-driven finder with incremental loading ("Show 24 more"). Do **not** assume the first page contains all filtered results.
- A previous Cabins41 workflow run found 369 structured solo-fare records (368 after cross-source deduplication). Difference from the displayed 439 is **not proof** of missing qualifying deals. Compare unique stable sailing identifiers, dates, and any fare/cabin distinctions, then assess freshness.
- **Never reject a sailing solely because its supplement is near 50%.** The supplement is useful descriptive data. No unapproved default cutoff.
- A comparison is reliable only if the solo and sharing prices correspond to the same sailing, cabin grade, fare type, currency and inclusions.
- No live site updates until the complete finder retrieval and fare matching have been tested.

Next engineering work:
1. Inspect the finder network requests or embedded structured data to find its pagination/API and solo-only filter; avoid unbounded crawling.
2. Enumerate all filtered pages, record total count and unique IDs, and reconcile with the 369 already captured.
3. Join solo and sharing prices from the same structured record or verified sailing page, not merely by ship/date.
4. Export review CSV, check duplicates/expired sailings, and leave uncertain records unpublished.

## Verified finder behaviour (12 November)

Opening `https://www.getthatcruise.co.uk/cruises?chips=solo` in a non-interactive HTML reader returns the **unfiltered** 2,215-sailing finder, showing the first 24 records, despite the `chips=solo` query parameter. The page displays "Solo fare published 439" as a filter option, not a result count. Therefore, **do not treat the query string as proof the filter was applied**.

The finder has "Show 24 more" incremental loading. A reliable extractor must confirm the *filtered result count* in its response and discover the actual API / browser request used by the filter and pagination. If that cannot be verified, fail closed and leave the existing 369 leads in manual review.

The 439 figure is the public filter's advertised count, **not** a verified enumeration of 439 unique retrieved solo-fare records.
