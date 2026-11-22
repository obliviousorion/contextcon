# Raise eval set: 15 held-out rounds (Jul 14 – Oct 27, 2026)

Each round's lead investor was checked against a news article on 2026-11-21. **The ground truth is the lead named in the press**, so the eval doesn't depend on whether Crustdata has recorded the round yet. Run each case with `cutoff_date = round_date`. Count a hit if ANY lead lands in the top-k, after normalizing names.

## At 9 AM, before running the eval
- Check each domain with Company Identify. These seven are unconfirmed: reo.dev, carpl.ai, revspot.ai, hunar.ai, clueso.io, auxoai.com, simplismart.ai.
- Drop any case that Crustdata can't resolve. Also drop any case with fewer than 5 peers that have funding data.
- **Leakage check:** confirm the cutoff filter removes the held-out round from both the startup and its peers.

## Expected hard cases (expect misses)
- CARPL (IFC is a development lender).
- Simplismart (Dallas VC rarely leads).
- Co-leads count as a hit if either lead appears. For Integral, match Mosaic, not Reid Hoffman.

## Recognizable to judges
- Simplismart: TechCrunch coverage, with Nvidia and Accel in the round.
- Superleap: Peak XV Surge.
- Raindrop: a YC alum, led by CRV.

## Alternates if cases drop
- Parallel Loop: Seed, led by 3one4, 2026-10-14.
- Shamrock AI: Seed, led by Endiya, 2026-10-15.
- Graph AI: Series A, led by Insight Partners, 2026-09-11.

None of the alternates are fully checked yet.

## eval/cases.json
```json
[
{"startup_name":"Reo.Dev","domain":"reo.dev","country":"India","sector":"AI sales intelligence for companies selling to developers","round_type":"Series A","amount_usd_approx":11300000,"round_date":"2026-07-16","actual_leads":["Elevation Capital"],"participants":["Heavybit","India Quotient","Gokul Rajaram"],"source_url":"https://inc42.com/buzz/exclusive-ai-sales-intelligence-startup-reo-dev-raises-11-3-mn-to-expand-in-us/"},
{"startup_name":"CARPL.ai","domain":"carpl.ai","country":"India","sector":"Radiology/medical imaging AI platform and marketplace","round_type":"Series A","amount_usd_approx":10000000,"round_date":"2026-07-23","actual_leads":["International Finance Corporation"],"participants":["Stellaris Venture Partners"],"source_url":"https://yourstory.com/2026/07/tech30-startup-carplai-raises-10-million-in-series-a-led-by-ifc"},
{"startup_name":"Revspot","domain":"revspot.ai","country":"India","sector":"AI sales automation and lead generation for high-ticket B2C sellers","round_type":"Series A","amount_usd_approx":4800000,"round_date":"2026-07-29","actual_leads":["Inflexor Ventures","Info Edge Ventures"],"participants":["Pentathlon Ventures","Silicon Road Ventures","Titan Capital"],"source_url":"https://inc42.com/buzz/revspot-raises-4-8-mn-to-scale-ai-sales-automation-platform/"},
{"startup_name":"Superleap","domain":"superleap.com","country":"India","sector":"AI-native enterprise CRM","round_type":"Pre-Series A","amount_usd_approx":4100000,"round_date":"2026-08-04","actual_leads":["Peak XV Partners (Surge)"],"participants":[],"source_url":"https://india.entrepreneur.com/business-news/superleap-raises-inr-36-cr-in-pre-series-a-led-by-peak-xvs-surge"},
{"startup_name":"Clueso","domain":"clueso.io","country":"US/India","sector":"AI agents for enterprise product video and documentation","round_type":"Series A","amount_usd_approx":10000000,"round_date":"2026-10-13","actual_leads":["Dharana Capital"],"participants":["Founders Future","Neotribe Ventures","Y Combinator","F7 Ventures"],"source_url":"https://inc42.com/buzz/clueso-bags-10-mn-to-automate-enterprise-video-creation-with-ai-agents/"},
{"startup_name":"Hunar.AI","domain":"hunar.ai","country":"India","sector":"Conversational AI for frontline workforce hiring","round_type":"Series A","amount_usd_approx":4500000,"round_date":"2026-10-20","actual_leads":["Blume Ventures"],"participants":["Hyderabad Angels Fund","Together Fund","Seedstars","AVNM Ventures"],"source_url":"https://india.entrepreneur.com/?p=100634"},
{"startup_name":"AuxoAI","domain":"auxoai.com","country":"US/India","sector":"Forward-deployed enterprise AI services and platform","round_type":"Series A","amount_usd_approx":20700000,"round_date":"2026-10-21","actual_leads":["NTT Venture Capital"],"participants":["George Still Jr","Amit Zavery","Giacomo Santina"],"source_url":"https://inc42.com/buzz/enterprise-ai-startup-auxoai-nets-20-7m-to-strengthen-its-fde-team/"},
{"startup_name":"Simplismart","domain":"simplismart.ai","country":"India","sector":"AI inference optimization infrastructure","round_type":"Series B","amount_usd_approx":14000000,"round_date":"2026-10-27","actual_leads":["Dallas Venture Capital"],"participants":["Nvidia","Accel","Shastra VC","Micromax"],"source_url":"https://techcrunch.com/?p=3181625"},
{"startup_name":"Runable","domain":"runable.com","country":"US/India","sector":"AI agent platform for small businesses","round_type":"Series A","amount_usd_approx":21000000,"round_date":"2026-08-27","actual_leads":["Susquehanna Venture Capital","Nexus Venture Partners"],"participants":["Together Fund","Array VC"],"source_url":"https://siliconangle.com/2026/08/27/runable-raises-21m-to-realize-small-businesses-growth-vision-using-ai-agents/"},
{"startup_name":"Chift","domain":"chift.eu","country":"Belgium","sector":"Unified API for accounting and financial data","round_type":"Series A","amount_usd_approx":12200000,"round_date":"2026-09-14","actual_leads":["BlackFin Capital Partners"],"participants":["Entourage","Shapers","Seeder Fund","Wallonie Entreprendre"],"source_url":"https://tech.eu/2026/09/14/chift-raises-eur105m-series-a-to-scale-financial-connectivity-across-europe/"},
{"startup_name":"AIUC","domain":"aiuc.com","country":"US","sector":"Insurance, audit and certification for AI agents","round_type":"Series A","amount_usd_approx":40000000,"round_date":"2026-09-16","actual_leads":["Ribbit Capital"],"participants":["First Harmonic"],"source_url":"https://www.securityweek.com/aiuc-raises-40-million-to-certify-enterprise-ai-agents/"},
{"startup_name":"Integral","domain":"integral.de","country":"Germany","sector":"AI-native accounting, tax and payroll for SMEs","round_type":"Series A","amount_usd_approx":21000000,"round_date":"2026-09-16","actual_leads":["Mosaic Ventures","Reid Hoffman"],"participants":["Cherry Ventures","General Catalyst","Puzzle Ventures"],"source_url":"https://tech.eu/2026/09/16/integral-lands-eur18m-series-a-for-ai-native-accounting-and-tax-services/"},
{"startup_name":"Magentic","domain":"magentic.com","country":"US/EU","sector":"AI agents for industrial procurement and supply chain","round_type":"Series A","amount_usd_approx":18000000,"round_date":"2026-09-17","actual_leads":["Felicis"],"participants":["Sequoia Capital","The Westly Group"],"source_url":"https://tech.eu/2026/09/17/magentic-raises-18m-to-automate-industrial-operations-with-ai-agents/"},
{"startup_name":"Raindrop","domain":"raindrop.ai","country":"US","sector":"Monitoring and testing for AI agents in production","round_type":"Series A","amount_usd_approx":35000000,"round_date":"2026-09-17","actual_leads":["CRV"],"participants":["Lightspeed Venture Partners","Y Combinator"],"source_url":"https://thenextweb.com/news/raindrop-series-a-50m-crv-agent-failures-simulations"},
{"startup_name":"Preference Model","domain":"preferencemodel.com","country":"US","sector":"RL environments and training data for frontier AI labs","round_type":"Seed","amount_usd_approx":16000000,"round_date":"2026-10-07","actual_leads":["Andreessen Horowitz"],"participants":["SignalFire","South Park Commons","Scale Angels"],"source_url":"https://pulse2.com/preference-model-raises-16-million-seed-round-led-by-andreessen-horowitz/"}
]
```
