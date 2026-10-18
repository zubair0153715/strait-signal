# Maritime / Supply-Chain Intelligence — Business Model

**Venture:** Strait Signal (working name — see §1)
**Wedge:** Dark-fleet / AIS-gap / ship-to-ship (STS) transfer alerts for ONE corridor: Strait of Hormuz crude.
**Status:** Planning document only. No product built, no customer contacted, no pricing quoted to any buyer, nothing registered, nothing bought.
**Sources:** All market/pricing figures in this doc are drawn from `~/workspace/research_notes/100m-niche-osint-data-business-20261013-1346/report.md` (web-derived research, dated 2026-10-13). Numbers from that report are directional, not verified by us. Anything the report labels speculative is labelled SPECULATIVE here. Anything we could not verify is labelled "unverified."
**Constraints:** Solo founder (Zubair, Pakistan-based), ZERO budget (free tiers only), nothing outbound without his explicit go-ahead, no fake data or fake pricing presented as quoted, no credentials anywhere, no terms-of-service violations.

---

## 1. Venture Name + Positioning

**Name (working): Strait Signal**

**One-line positioning:** "We alert your desk within 24 hours when a tanker goes dark, does a ship-to-ship transfer, or changes destination in the Strait of Hormuz — with satellite evidence and a confidence score, not a map of ships."

**Why this name:**
- Names the corridor (Strait of Hormuz) and the product (a signal/alert, not a globe).
- Short, pronounceable, descriptive of the wedge rather than of a generic tracking platform.
- Distinct from the incumbent names in the research report (Kpler, Vortexa, MarineTraffic, VesselFinder, S&P Global, project44, FourKites, Dataminr).

**What is NOT claimed:**
- Trademark availability: **unverified.** No trademark search has been run.
- Domain availability: **unverified.** No domain has been checked, registered, or bought.
- Company registration: none. This is a working name for a planning document, not a registered entity.
- Before any public launch, run a trademark/domain check and confirm the name is clear. If it collides, rename — the wedge matters, the name does not.

**What this venture is NOT:** PharmaReg AI is a separate business. This is a new, separate lane. No shared customers, pricing, or branding are assumed.

---

## 2. The Wedge: Exactly What the Product Detects

### The core insight

Raw ship tracking is free (MarineTraffic, VesselFinder). Nobody pays for a map of ships. Buyers pay for **one painful answer with a timestamp and evidence**: *did something anomalous happen in my corridor, involving which vessel, when, where, and how confident are you?*

The wedge is **ONE corridor (Strait of Hormuz), ONE commodity (crude), ONE buyer pain (dark-fleet / AIS-gap / STS risk)**. No generic globe. No "track every ship everywhere."

### What the product detects

| Signal | Detection rule (initial, to be validated against real data) | Why a buyer cares |
|---|---|---|
| **AIS-gap event** | A vessel that was transmitting AIS in/near the corridor stops transmitting for ≥ a defined threshold (initial working threshold: 24h; tune from observed data), then reappears — or never reappears within the observation window. | A vessel going dark in a chokepoint is the classic precursor to an undisclosed transfer, a sanctions-risk port call, or a spoofed identity. |
| **STS transfer candidate** | Two vessels (typically a large tanker + a smaller tanker / shuttle) come within close proximity (working threshold: < 500 m, unverified — tune from data) at low speed (< 3 knots, working threshold) for a sustained period (working threshold: > 2 hours) in open water / outside a port anchorage, with one or both vessels showing an AIS gap before, during, or after the rendezvous; corroborated where possible by Sentinel-1 SAR contact with no matching AIS. | STS transfers at sea are how cargo changes hands without a port record. A compliance desk wants to know it happened; a trader wants to know the cargo moved. |
| **Destination change** | A vessel's AIS-reported destination field changes mid-voyage in/near the corridor, especially combined with a course change inconsistent with the original destination. | Signals a diverted cargo — affects ETA, arbitrage, and counterparty-risk assessment. |
| **Draught change** | A vessel's AIS-reported draught changes materially (working threshold: ≥ 2 m, unverified) without a port call in between — consistent with loading or discharging cargo at sea. | Corroborates an STS candidate: a vessel that "got heavier/lighter" mid-ocean likely transferred cargo. |
| **SAR contact with no AIS match** | A Sentinel-1 SAR radar contact in the corridor has no AIS-transmitting vessel within a matching radius/time window (working threshold: 2 NM / 30 min, per the research report's demo correlator). | The independent evidence layer: radar sees hulls whether or not they broadcast AIS. This is what turns "AIS went quiet" into "something was physically there." |

**Detection inputs (free tiers only):**
- AISStream (free terrestrial AIS) — known limitation: regional gaps and latency; misses open ocean. The demo must state coverage and latency honestly.
- Copernicus Sentinel-1 SAR (free, ~20 m) — radar, works day/night/through cloud.
- Copernicus Sentinel-2 optical (free, ~10 m) — daytime, clear-sky corroboration where available.
- VIIRS night lights + public port schedules — secondary corroboration.
- Satellite AIS is **paid** and therefore **out of scope** for the zero-budget build. The product must be honest that it is a terrestrial-AIS + SAR product, not a satellite-AIS product.

**Manual review before any alert ships.** At this stage, accuracy beats automation. Every candidate event is human-reviewed before it goes to a buyer. No fully automated alerting until the false-positive rate is measured and documented.

### What an alert contains

Every alert is a self-contained, auditable record:

1. **Vessel identity:** name (as reported), MMSI, IMO (where available), flag, vessel type, deadweight / size class (where available). If identity is uncertain, say so — never guess an IMO.
2. **Event type:** AIS-gap / STS candidate / destination change / draught change / SAR contact with no AIS match (one or more, as applicable).
3. **Timestamps:** first-observed time, last-AIS time, reappearance time (if any), SAR acquisition time — all in UTC with explicit timezone labelling.
4. **Location:** lat/lon of last AIS position, SAR contact position, and (for STS candidates) rendezvous centroid — with the matching radius used.
5. **Evidence:** the specific observations behind the call — e.g. "AIS last seen 2026-XX-XX 04:12 UTC at 26.5°N, 56.3°E; Sentinel-1 acquisition 2026-XX-XX 18:40 UTC shows radar contact at 26.6°N, 56.4°E with no AIS match within 2 NM / 30 min; draught changed from X m to Y m."
6. **Confidence score + reasoning:** e.g. High / Medium / Low with a one-line reason ("High: SAR contact + AIS gap + draught change all coincide"). Confidence definitions must be written down, applied consistently, and revisable from measured false-positive data — not invented per alert.
7. **Provenance:** data sources used, acquisition times, processing version, and the coverage/latency caveat for that event.
8. **Explicit non-claims:** what the alert does NOT assert (see below).

**Delivery:** daily/weekly alert feed (CSV + email) + weekly brief in the pilot. No real-time SLA is offered — a solo builder on free feeds cannot guarantee 24/7 uptime, and promising it would be dishonest.

### What the product explicitly does NOT claim

- **Never label a vessel "sanctioned"** without an official sanctions-list match. The correct language is: *"AIS-gap event, SAR contact, matches pattern X."*
- **Never label an event "sanctions evasion."** Evasion is a legal conclusion about intent. The product reports observable behaviour (gap, rendezvous, draught change), not intent or legality.
- **Never assert a vessel's identity** when the evidence is ambiguous (spoofed MMSI, reused identity, missing IMO). Report the uncertainty.
- **Never assert cargo type, cargo origin, or ownership** unless directly evidenced. Draught change suggests a transfer happened; it does not prove what was transferred.
- **Never present a simulated, synthetic, or backfilled event as real.** Any demo/test event is labelled SIMULATED in the artefact itself.
- **Never guarantee detection completeness.** Free terrestrial AIS has gaps; Sentinel revisit is not continuous. The product reports what it detected, with stated coverage limits — not "all dark activity in Hormuz."

---

## 3. Three Sellable Products + Pricing Ladder

### Pricing anchors (sourced from the research report)

| Anchor | Value (per research report) | Status |
|---|---|---|
| MarineTraffic Essential | £100/user/month | Sourced (secondary compilation in report) |
| MarineTraffic Basic | £10/user/month | Sourced (secondary compilation in report) |
| VesselFinder Satellite | $139/month or $1,399/year (ex-VAT) | Sourced (secondary compilation in report) |
| Dataminr Pulse entry tier | ~$50k/year (secondary estimate) | Sourced as secondary estimate; not a published list price |
| project44 / FourKites base | ~$15k/yr / ~$12k/yr (secondary compilation) | Directional; both custom enterprise pricing in practice |
| Kpler enterprise | No published list price; secondary estimate: single-module from low five figures/yr; full bundles low-to-mid six figures/yr | Secondary estimate only — NOT a quote |
| Kpler ARR | Reported $300–400M ARR (2026) | Sourced (secondary reporting) |

**Pricing rule for this venture:** Every price below is **SPECULATIVE** — reasoning from the anchors above, not a quoted price. The report labels the maritime pricing ladder speculative, and this doc preserves that label. Real pricing is set by what pilot customers actually agree to pay, not by this document.

### Product A — Dark-Fleet / Sanctions-Risk Alert Feed (RECOMMENDED WEDGE, build first)

**What it is:** Daily/weekly alerts for AIS-gap events, STS candidates, destination/draught changes, and SAR contacts with no AIS match in the Strait of Hormuz crude corridor. CSV + email + weekly brief. Manual review of every alert before delivery.

**Who it is for:** Compliance analysts, trade-finance sanctions teams, insurer sanctions screening, and commodity-desk risk (see §4).

**Pricing (SPECULATIVE):**
- 90-day paid pilot: **$3k–5k/month** ($9k–15k total) — see pilot terms below.
- Post-pilot annual: **$36k–60k/year per desk** for one corridor (SPECULATIVE, anchored to MarineTraffic Essential + Dataminr entry tier).
- Expansion: **$96k–150k/year** for 3 corridors + API + compliance export (SPECULATIVE — validate against what pilot customers actually pay).

**Why first:** It is the only product where free data (AIS + Sentinel-1 SAR) produces evidence a buyer cannot get from a free map, and where the buyer's pain (sanctions/compliance risk) is urgent rather than speculative.

### Product B — Single-Commodity Flow Tracker (Hormuz Crude)

**What it is:** Weekly tracker of crude flow through the Strait of Hormuz: vessel counts, laden/draught inference, weekly flow vs 4-week average, next-7-day ETA list for named vessels. One corridor, one commodity.

**Who it is for:** Commodity trading desks (chartering, arbitrage timing), refiners, energy analysts.

**Pricing (SPECULATIVE):**
- 90-day paid pilot: **$3k–5k/month** (same pilot structure as Product A).
- Post-pilot annual: **$36k–96k/year** (SPECULATIVE; report range $3k–8k/month → $36k–96k/year).
- Note: this product competes more directly with Kpler/Vortexa flow data, so the wedge must be a specific buyer pain (e.g. "your corridor, your counterparties") rather than generic flow numbers.

### Product C — Port-Congestion + ETA Exception Alerts for ONE Port

**What it is:** Exception alerts for ONE port (to be chosen in Week 1 — the port must serve the Hormuz crude corridor or a named pilot customer's import flow): berth queue, dwell time, ETA slip > 24h, with AIS + port-schedule evidence. Exception-only: no alert when nothing changed.

**Who it is for:** Freight forwarders, 3PLs, shippers/importers with cargo through that port.

**Pricing (SPECULATIVE):**
- 90-day paid pilot: **$1k–3k/month** (lower entry price; report range $1k–3k/month per shipper/forwarder).
- Post-pilot annual: **$12k–36k/year** per shipper/forwarder (SPECULATIVE).
- Trade-off: lower price and faster sale, but needs volume to matter. Do NOT build this first unless a pilot customer for Product A or B explicitly asks for it — it is the easiest to commoditise and the furthest from the dark-fleet differentiation.

### Pilot pricing (applies to all three products)

- **90-day paid pilot: $3k–5k/month for Products A/B; $1k–3k/month for Product C** (SPECULATIVE).
- **Paid, not free.** Free pilots get no attention and no honest feedback. $3k/month is cheap enough for a desk head to approve and expensive enough to force a real evaluation.
- **Written success criteria, agreed upfront, before the pilot starts.** Example for Product A: *"Detect ≥80% of AIS-gap events >24h in the corridor, with <20% false positives, verified against the customer's own data / incumbent feed."* The exact thresholds are negotiated per pilot and written into the pilot agreement; the example numbers above are starting points, not guarantees.
- **No exclusivity** in the pilot unless the buyer pays a premium for it — exclusivity caps the market.
- **One corridor, one buyer team, one delivery format** per pilot. Scope creep is the pilot-killer.

---

## 4. Target Buyer Personas

### Persona 1 — Desk Head (commodity trading desk)

- **What they care about:** Cargo timing, arbitrage windows, demurrage avoided, not being blindsided by a diverted cargo or a counterparty's dark vessel. One missed event costs more than a year of subscription.
- **Likely objection:** "We already get this from Kpler in our bundle. Why pay you too?"
- **Proof they need:** One specific event in the last 30 days that your alert caught faster — or that their incumbent missed — documented with timestamps, not anecdote. Plus a 2-minute demo on *their* corridor, not a generic globe.
- **How to win:** Personalised demo ("here are 3 events involving vessels that called at your ports in the last 14 days"). Ask: "Would this have changed a decision in the last 30 days?"

### Persona 2 — Compliance Analyst (trading house / shipowner / operator)

- **What they care about:** Not facilitating a sanctions violation. An auditable trail showing *why* a vessel was flagged, what evidence existed, and what was NOT claimed. Defensible process matters more than speed.
- **Likely objection:** "Your alert isn't an official sanctions-list match. We can't act on a 'pattern.' And if you're wrong, you've defamed a vessel."
- **Proof they need:** Provenance and timestamps on every alert; explicit non-claims language; a documented manual-review step; a false-positive rate measured on real data; confirmation that alerts say "matches pattern X," never "sanctions evasion."
- **How to win:** Lead with the audit trail and the non-claims language. Offer the compliance-export format (CSV with source + timestamp + confidence + reviewer) as a pilot deliverable.

### Persona 3 — Chartering Desk (tanker owner / charterer)

- **What they care about:** Where tonnage actually is, which vessels are genuinely available vs dark/engaged, ETA reliability for fixing the next voyage. A vessel that "disappeared" may be unavailable — or may be the counterparty's hidden capacity.
- **Likely objection:** "AIS gaps are normal — vessels lose signal, crews switch AIS off in high-risk areas. Your 'dark fleet' is mostly noise."
- **Proof they need:** A measured false-positive rate, with the noise cases shown honestly (e.g. "these 3 gaps were terrestrial-AIS coverage gaps, not dark activity — here's how we distinguish them"). SAR corroboration is what separates signal from noise.
- **How to win:** Show the SAR layer. Show that you distinguish coverage gaps from genuine dark behaviour — and that you say so when you cannot tell.

### Persona 4 — Trade-Finance Sanctions Team (bank)

- **What they care about:** Whether the vessel carrying the cargo they are financing has anomalous behaviour that creates sanctions / reputational exposure for the bank. They need a screening input, not a trading signal.
- **Likely objection:** "We have a sanctions-screening vendor and a legal review process. A solo builder's feed doesn't meet our vendor-diligence, SLA, or data-governance bar."
- **Proof they need:** Written methodology, provenance/timestamps, data-retention and correction policy, and a clear statement of what the feed is (a screening *input*, not legal advice or a sanctions determination). Expect the longest sales cycle of any persona.
- **How to win:** Do not pitch banks first. Banks are a Year-2 buyer, after the product has paying trading/compliance customers and a documented track record. In the 90-day plan, banks are demo targets only if a warm introduction exists — never the first pilot target.

### Persona 5 — Insurer (marine / war-risk / cargo underwriter)

- **What they care about:** Sanctions-exposure screening on insured vessels, and voyage-risk assessment (is this vessel behaving anomalously in a high-risk chokepoint?). A cleaner risk book and fewer sanctions surprises.
- **Likely objection:** "Our underwriting and sanctions screening already use incumbent data. Your coverage is one corridor, your uptime is unproven, and we need an SLA."
- **Proof they need:** Coverage/latency stated in writing; a documented track record over at least one pilot; evidence that alerts are auditable and correctable; no safety-critical or coverage-guarantee claims.
- **How to win:** Position as a *supplemental* screening input for one corridor, not a replacement for their incumbent. Offer the pilot as a 90-day parallel run against their existing screening, scored on events their process missed.

**Cross-persona note:** The giants (Trafigura, Vitol, Gunvor, Mercuria, Cargill/Flexport per the research report) already buy Kpler/Vortexa/S&P. A solo builder will not displace that contract in 90 days. The realistic first pilot comes from **one desk / one analyst team inside a giant, or a mid-tier trader/forwarder/broker** who cannot afford the full Kpler bundle. Demo to giants for learning; sell to the mid-tier for revenue.

---

## 5. 90-Day Demo-First Plan

### Weeks 1–2 — Build ONE wedge, not a platform

**Day 1–3: Pick and write down**
- ONE corridor: Strait of Hormuz.
- ONE commodity: crude.
- ONE buyer pain: dark-fleet / AIS-gap / STS risk for compliance desks.
- One-sentence value prop (see §1). If it doesn't fit in one sentence, the wedge is too broad.

**Day 4–10: Build the pipeline (free tiers only)**
- AISStream (free terrestrial AIS) → Postgres/PostGIS.
- Copernicus Sentinel-1 SAR downloads for the corridor.
- Simple correlator: SAR contact with no AIS match within 2 NM / 30 min = candidate dark event; draught + destination change flags.
- Manual review of every candidate before it becomes an alert. Accuracy > automation.

**Day 11–14: Build the demo artefact**
- One live web page (map + event table + evidence) + one 5-slide PDF + one 2-minute video, all using **real** data from the last 14 days.
- Include coverage/latency caveats in writing. No fake data. No simulated events without a clear SIMULATED label.

**Deliverable by Day 14:** A demo a named analyst can verify in 10 minutes.

### Weeks 3–4 — Demo to 20 targets (demo-first, no asking for money yet)

- Send **personalised** demos to 20 targets: 5 named giants (Trafigura, Vitol, Gunvor, Mercuria, Cargill/Flexport — per the research report) + 15 mid-tier traders, forwarders, brokers, and trade-finance / sanctions teams.
- Each demo is personalised: "Here are 3 events in *your* corridor / involving vessels that called at *your* ports in the last 14 days."
- Ask for ONE thing: a 20-minute call to answer: "Would this have changed a decision in the last 30 days? What would make it worth paying for?" Do not pitch pricing on the first call.
- Track: reply rate, call rate, and the *specific* feature each prospect asks for.

**Deliverable by Day 28:** 5–10 conversations, 1–3 prospects who say "send me this weekly."

**Note on outreach:** Nothing outbound is sent under this plan without Zubair's explicit go-ahead for the exact message and recipient list. This document plans the outreach; it does not authorise it.

### Weeks 5–8 — Paid pilot

- Offer a **90-day paid pilot** (see §3 pilot terms): $3k–5k/month for Product A/B, $1k–3k/month for Product C, with written success criteria agreed upfront.
- Deliver: daily/weekly alerts for ONE corridor, CSV + email + 1 call/month.
- Measure from Day 1: detection rate vs the agreed criterion, false-positive rate, and every prospect-requested feature (log it verbatim — that log is the roadmap).
- Do not offer exclusivity unless the buyer pays a premium for it.

**Deliverable by Day 56:** ≥1 signed paid pilot, or the kill criteria below are being triggered (see §5, Kill criteria).

### Weeks 9–12 — Confirm or kill

**Confirm (double down) if ≥2 of these are true:**
1. ≥2 paid pilots signed at $3k+/month, OR ≥1 pilot converts to an annual $36k+ contract.
2. ≥3 prospects independently name the *same* missing feature (e.g. "add LNG," "add STS evidence photos," "add sanctions-list match") — that is the roadmap.
3. Alerts beat the buyer's incumbent on at least one *specific* event (faster, or an event they missed) — documented with timestamps, not anecdotal.

**KILL criteria (mandatory — a plan that cannot kill the idea is a hobby):**

| # | Kill signal | Threshold |
|---|---|---|
| K1 | No paid pilots | **0 paid pilots after 30+ personalised demos + 10+ calls.** "People liked it" does not count — *paid* pilots count. |
| K2 | Kpler-bundle objection with no named gap | Prospects say "we already get this from Kpler / S&P for free in our bundle" **and cannot name a gap** the wedge fills, across the majority of substantive conversations. |
| K3 | False positives too high | False-positive rate **>30%** after manual review, on measured data. |
| K4 | Corridor unmonitorable with free feeds | Coverage gaps make the corridor unmonitorable with free feeds (e.g. open-ocean stretches with no terrestrial AIS, Sentinel revisit too slow to corroborate events) — documented, not assumed. |

**On kill:** Stop. Do not "keep polishing." Choose one pivot, or shut the lane down:
- Pivot A: change corridor/commodity (e.g. Hormuz crude → Black Sea grain, or LNG to NW Europe).
- Pivot B: change buyer (e.g. traders → insurers/banks for sanctions screening).
- Pivot C: sell the same signal as alt-data to a mid-size fund with a backtest (different buyer, different proof burden — see the research report §2).
- Each pivot restarts the 90-day clock with its own kill criteria. A pivot is not a reason to drop the kill criteria.

### After Day 90 (if confirmed)

- Expand corridor-by-corridor (Hormuz → Malacca → Black Sea → Panama/Suez), commodity-by-commodity (crude → LNG → grain → metals).
- Add the second channel: package the same signal as a backtested alt-data feed for funds (via Neudata / Snowflake-type marketplaces — marketplace mechanics per the research report).
- Hire / partner for reliability (24/7, SLA) before chasing $100k+ enterprise contracts. Solo caps at ~$0.5–2M/year (see §6); $100M needs a team + channel partners.

---

## 6. Honest $100M Math

**$100M is a COMPANY outcome over 7–12 years, not a solo outcome, and not a 1–3 year outcome.** Anyone promising $100M in year 1–2 from zero-budget OSINT is selling a course, not a business. Kpler took ~11 years, ~800–1,000 staff, $1B+ investment, and multiple acquisitions to reach its reported scale.

| Path | Math | Verdict |
|---|---|---|
| Enterprise-heavy | 200 customers × $500k/yr = $100M | Not credible solo. Only Kpler/Vortexa-scale firms charge $500k; needs a multi-module platform + sales team. |
| Mid-market realistic (wedge + expansion) | 1,000 customers × $100k/yr = $100M | Hard but structurally possible over 7–12 years *if* the product expands to 3–5 corridors/commodities and adds API + compliance modules. 1,000 mid-market buyers is a large sales organisation. |
| Volume / SMB | 4,000 × $25k/yr = $100M | Possible only with self-serve + marketplace distribution; churn will be brutal because AIS data is commoditised. |
| Most plausible solo-to-scale path | 50 anchor customers × $100k + 500 × $100k via partnerships/resale (data + alerts + API) | Still requires a team, 24/7 reliability, and either capital or a channel partner. |
| **Solo ceiling** | **~$0.5–2M/yr** | The realistic cap for one person on this product: a handful of pilots + annual contracts, daily/weekly (not real-time) delivery, manual review. |

**What $100M requires that solo does not have:** 200–1,000 paying organisations (or a few $1M+ government/enterprise contracts like Dataminr's reported $318M Pentagon contract — which a solo builder cannot win without procurement track record), a multi-corridor/multi-commodity platform, 24/7 reliability with an SLA, a sales organisation, and either capital or a channel partner.

**The honest target for this venture in Year 1:** 1–3 paid pilots → 1–2 annual contracts at $36k–60k/year (SPECULATIVE pricing). That is $36k–120k in first-year revenue if the wedge works — a real business start, and roughly 0.1% of $100M. The $100M framing is a direction (build a wedge that *can* expand corridor-by-corridor), not a forecast.

**Do NOT hype.** Do not put "$100M" in a pitch deck as a projection. Do not present the pricing ladder in §3 as quoted prices. Do not present the research report's market-size figures ($3.8B AIS analytics, $3.2B maritime information) as this venture's addressable market — the report itself states the single-wedge TAM is plausibly $50–300M (SPECULATIVE estimate), and that $100M revenue requires expansion to several corridors/commodities over years.

---

## 7. Legal Red Lines

These are hard constraints, not guidelines. Violating any of them ends the venture's credibility — and may create legal exposure — faster than any competitor could.

1. **No named-person tracking.** The product tracks vessels, not people. Never identify, track, or report on individual crew members, owners as private individuals, or any person's location. No crew lists, no personal data.
2. **No military / private-jet targeting product.** This venture is maritime commercial shipping only. Do not build, offer, or repurpose the pipeline for military vessel targeting, private-jet tracking, or any product aimed at the location of specific individuals or military assets.
3. **No safety-critical claims.** Never claim the feed can be used for navigation, collision avoidance, search-and-rescue, or any safety-of-life decision. Alerts are commercial/compliance information with stated latency and coverage gaps — not a safety system.
4. **Provenance + timestamps on every alert.** Every alert carries: sources used, acquisition times, processing version, and the coverage/latency caveat. If provenance cannot be stated, the alert does not ship.
5. **No defamatory labels.** Never write "sanctions evasion," "smuggling," "illicit," or "sanctioned" about a named vessel without an official sanctions-list match (and even then, report the match factually: "Vessel X appears on [official list], [date], [entry]" — with a link to the official entry). Default language: "AIS-gap event, SAR contact, matches pattern X." A wrong public accusation is a defamation risk; the product's value is the observable behaviour, not the accusation.
6. **Sanctions advice is not given.** The product is a screening *input*, not legal advice and not a sanctions determination. Every customer-facing document says so. Sanctions determinations belong to the customer's legal/compliance function.
7. **Respect source API terms.** Use AISStream, Copernicus Sentinel, and any other source only within their published terms (free-tier rate limits, attribution, redistribution rules). Do not scrape a source that prohibits scraping; do not resell raw data a licence forbids reselling; do not circumvent rate limits or access controls. If a needed input is paid-only or licence-restricted, the product works without it or does not launch that feature.
8. **Correction policy.** When an alert is wrong, issue a dated correction to every recipient of the original alert, keep the correction in the audit trail, and count the error in the false-positive rate. Hiding errors destroys the trust the product sells.
9. **Data retention + audit trail.** Keep the underlying observations behind every shipped alert (AIS records, SAR acquisition IDs, processing version) so any alert can be re-verified later. Do not delete evidence behind a disputed alert.
10. **No credentials, no scraping of private data.** No credentials are stored in this venture's code, docs, or chat. No access to non-public, paywalled, or login-gated data is sought or used. All inputs are public/free-tier sources used within their terms.

---

## Appendix: What Is Speculative vs Sourced

**Sourced (from the research report, with URLs in that report):** Kpler ARR/valuation, Spire Maritime deal, MarineTraffic/VesselFinder prices, Dataminr pricing anchor, Neudata spend/pricing ranges, parametric premium pool ranges, free-feed availability (AISStream, Sentinel, USGS/GDACS/NOAA/NASA), marketplace mechanics (Neudata/Snowflake/Datarade).

**SPECULATIVE (labelled as such in this doc):** The $100M math paths, the $36k–150k/year maritime pricing ladder, the $3k–5k/month pilot price, the $2–10M realistic ceiling for niche data vendors, the $50–300M TAM for one wedge, and all "most plausible" timelines. These are reasoning from sourced anchors, not quoted prices. Validate them by *selling*, not by reading more reports.

**Unverified:** Venture-name trademark/domain availability; the working detection thresholds in §2 (24h gap, 500 m / 3 knots / 2 h STS, 2 m draught change) — these are starting points to tune from real data, not validated parameters; any per-customer success-criterion numbers until negotiated with that customer.
