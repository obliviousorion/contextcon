# Two-minute demo

Use the **Detention overcharge** packet from a fresh demo database: start with `python offline_server.py --fresh` (or `./start-freightclose.command --fresh`). To show a real dated rate without a model key, also set `FREIGHT_FX=live`. For a competition recording, validate live credentials and the dated FX quote first. Use the mode displayed by the app when speaking. Use the INR amount and quote date displayed in your own receipt.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | Show the carrier invoice, with the $450 detention line visible. | “A carrier says our truck waited three billable hours. The delivery record says it was there for two hours total. An Indian logistics firm pays someone to catch that difference, book the right amount and explain the deduction to the carrier.” |
| 0:15–0:33 | Point to the $2,400 base, $150 hourly rate, 60 free minutes and 120-minute dwell. Click **Audit and settle**. | “Here’s the whole job. Juniper Freight invoiced $2,850 on this Dallas-to-Tulsa shipment. FreightClose reads the bill, matches its purchase order and checks the charges against the contract and delivery evidence.” |
| 0:33–0:54 | Point to the **Line-item audit** row for detention ($450 billed, $150 supported, $300 withheld), then the open **Price detention** step with its minutes, rate and source references. | “The first hour of waiting is free. That leaves exactly one completed billable hour at $150. The invoice asks for $450. You can trace this $300 deduction back to these records and recompute it yourself.” |
| 0:54–1:13 | Point to the **Spending authority** meter: INR exposure against the cap, the rate and its date. Scroll to the ledger posting and the itemized short-pay notice. | “Our controller authorizes spending in rupees. This dated exchange-rate check determines whether FreightClose may post the dollar liability. The result is a $2,550 payable and a $300 short-pay notice in our local sandbox.” |
| 1:13–1:27 | Click **Audit and settle** again. Point to the blue **Duplicate blocked** banner and the case-history count (still one payable). | “Suppose someone clicks twice. This invoice already has a settlement. The same payable cannot be posted twice. Finance can download the receipt with its reasons.” |
| 1:27–1:47 | Select **Missing delivery record**, run it, then enter 120 and `Signed gate log GL-018`. | “Now the same kind of bill arrives without proof of waiting time. The desk holds it. Nothing gets booked. The reviewer has one specific task: find the signed gate record and enter its verified dwell time.” |
| 1:47–2:00 | Click **Attach evidence and re-audit**. Show the updated decision and receipt. | “The reviewer supplied evidence. FreightClose reran the contract and authority checks and closed the case. That's the paid work we replace: reconciling a freight bill and posting exactly what the evidence supports.” |

### Sample carrier input

```text
Carrier: Juniper Freight Co.
Lane: Dallas, TX to Tulsa, OK
Currency: USD
Invoice ID: JF-8217
PO: PO-60417
Linehaul: $2,400.00
Detention: $450.00
Total due: $2,850.00
```

**If a live source fails while recording**, show the hold, the missing source and the absence of postings. A separate offline rehearsal can demonstrate the contract arithmetic. Label it as a fixture run.

**For submission**, publish a single accessible two-minute recording and link the architecture section of the public README. The organizers also request the repository URL, team details and a declaration of pre-event work where applicable.
