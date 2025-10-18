---
aliases:
- Visa Status Check
- Check Visa Type and Status
- 9G Visa Status Query
- 9G blacklist check
- Blacklist Status Check
- Immigration Status Check
department: BureauOfImmigration
name: 9G Visa Status Check
slug: 9g-visa-status-check
type: solo_task
updated_at: '2025-10-17'
---

# 9G Visa Status Check

## Summary

The 9G Visa Status Check is a short standalone service to verify an individual's current immigration classification and record with the Bureau of Immigration (BI). Typical uses: confirm whether a person holds a 9G work visa or a 9A tourist visa, check whether an individual is on any blacklist or has a DERO (derogatory) record, and obtain the official BI record summary needed before filing downstream tasks (e.g., 9G application, I-Card cancellation, downgrade, extension). This service is used when a client or employer needs authoritative confirmation of BI status before deciding the next immigration action.

---

## Background prerequisites

Customers must meet the following conditions to request this service:

- Geographic prerequisite: The client or an authorized local representative should be in the Philippines when BI requires originals or in-person verification. Some preliminary checks can be performed remotely but final confirmation often needs BI visit or official channel query.
- Relationship prerequisite: The requester must be the visa holder, the employer/HR acting for the visa holder, or an authorized representative with a signed authorization letter accepted by BI.
- Business prerequisite: The client should provide identifying information (passport number, full name, date of birth) and any BI submission receipts or reference numbers if available.

Not eligible:
- Cases where the client cannot provide minimal identity details or no authorized representative is available when BI requires the principal's physical presence.

---

## Required documents

### Documents client must provide

- Passport bio page (copy and, if requested, original): identity verification. Original may be required by BI for in-person queries.
- Passport number and full name as it appears on passport: for BI query matching.
- BI submission receipt or BI reference number (if available): speeds locating records in BI.
- I-Card copy (if holder has one): helps locate BI I-Card record faster.

### Documents the service can produce

- Official Status Summary (producer: 9G Visa Status Check)
  - document: "BI Status Check Report"
  - producer: 9G Visa Status Check
  - path: BureauOfImmigration/9g-visa-status-check.md
  - usage: A short report confirming visa classification (9G / 9A / other), blacklist/DERO status, and recommended next steps.

---

## Documents obtained after completion

- BI Status Check Report (digital PDF): contains the verified visa type, any blacklist/DERO flags found, BI reference numbers, and short actionable recommendations.
- If BI provides additional official receipts or notes during the visit/query, copies are returned to the client as attachments.

---

## Process / Steps

**Total estimated duration:** Same day to up to 5 business days depending on BI channel and complexity of record search.

### Step 1: Intake and identity verification

**Estimated duration:** Same day (hours)

Specific actions:
1. Client submits passport details and any BI reference numbers or prior receipts.
2. Agent confirms scope (status check only, or status check + follow-up actions) and obtains signed authorization when agent will query on behalf of client.

**Needed documents:** passport copy, BI receipt/reference (if any)

**Note:** If the client is outside the Philippines and BI demands physical presence, an authorized local representative with a notarized authorization may be necessary.

---

### Step 2: Query BI records (method depends on available channels)

**Estimated duration:** Same day to 2–3 business days

Specific actions:
1. Query BI via the visa section, MISD (Management Information Systems Division) if accessible, or by visiting the BI records counter in person.
2. Verify visa classification (9G, 9A, 13A, 9F, etc.), check for blacklist or DERO entries, and look for existing orders, I-Card records or previous submissions.
3. If MISD returns no record, escalate to visa section or direct BI records office as MISD may not show complete information.

**Completion sign:** Agent obtains a BI confirmation (screenshot/print/official note) or a detailed case note confirming the current status.

**Caveat:** MISD may not provide centralized query support; visa section often provides explanations or confirms blank results.

---

### Step 3: Deliver status report and recommended next steps

**Estimated duration:** Same day (after query result)

Specific actions:
1. Prepare the BI Status Check Report summarizing findings: visa class, expiry or endorsement details, blacklist/DERO status, relevant BI reference numbers.
2. Provide recommended next steps (for example: produce 9G order copy, schedule 9G extension, initiate downgrade and I-Card cancellation, or no action required).
3. If needed, propose follow-up services and link to producer tasks (9g-order-copy-request, 9g-application, 9g-visa-extension, 9g-downgrade-and-i-card-cancellation).

**Completion sign:** Client receives BI Status Check Report and confirms instructions to proceed if any further action is required.

---

## Price & Fees

No fixed retail price recorded. Typical handling fee is a modest one-off charge for an in-person BI visit or official query; remote checking (using provided receipts/reference numbers) may be offered at a lower fee. Any official BI fees for printed certified copies are charged separately by BI.

**Price notes:**
- If a BI visit or urgent same-day in-person query is required, an additional urgent handling charge may apply.
- If agent coordinates procurement of certified copies (for example 9G order CTC), that triggers additional service fees (use 9g-order-copy-request service).

---

## Important notes & restrictions

### Processing limitations
- MISD or online channels may not reflect full BI records; the visa section or records office often provides the definitive answer.
- BI may require the principal's in-person presence or an accepted signed authorization for certain queries or to release certified documents.

### Timing requirements
- Allow extra time when BI needs cross-branch record searches or when the client's name has multiple matches (identical names may require NTSP or further identity disambiguation).

### Risk warnings
- If BI finds enforcement flags (DERO, blacklists, Orders to Leave), further remedial processes are required (e.g., fines, downgrade workflows) that may have additional costs and time.
- Do not rely on informal statements; obtain written BI confirmation or a formal copy where downstream processes require documentary proof.

---

## Frequently Asked Questions

**Q: Can you confirm my status remotely without my passport?**
A: Basic checks using full name and passport number may be possible but will be less reliable. A passport number and copy are strongly recommended to avoid misidentification.

**Q: What if MISD shows no record?**
A: MISD may not be a complete centralized query source. If MISD returns no record, we will contact the visa section or visit BI records in person to confirm.

**Q: Will this check remove a blacklist or DERO entry?**
A: No. The status check only reports the presence of such flags. Remediation (payments, downgrading, appeals) requires additional services.

---

## Evidence sources

> The following lines summarize the chat evidence used to assemble this service.

- Message 56606 (2021-09-24): Request to check current visa type — 9G or 9A. (source: All Direction Processing group)
- Message 56608 (2021-09-24): Instruction to check if there are any DERO records associated with the individual. (source: All Direction Processing group)
- Message 627801626 (2022-10-06): Client asks how to check current visa status; agent notes visa section or MISD may be contacted and MISD may not have centralized queries; visa section can provide explanations. (source: Check current visa group)
- Message 251788 / 251806 / 251809 (2022-10-07): Examples of record checks: no record found, identified blacklist entry and visa type confirmations (9A). These illustrate common outcomes and required escalation to visa section.

**Data source files:**
- D:\AI_Projects\.TelegramChatHistory\Organized\groups\All Direction Processing_413089732.jsonl
- D:\AI_Projects\.TelegramChatHistory\Organized\groups\Check current visa_627801626.jsonl

---

## Document information
- Source file: 9g-visa-status-check.md
- Integration date: 2025-10-17
- Evidence items referenced: messages 56606, 56608, 627801626, 251788, 251806, 251809

---

## Related businesses
- name: "9G Application"
  path: "BureauOfImmigration/9g-application.md"
  reason: "If the status check confirms missing or incomplete 9G records, the 9G Application service is used to file or correct 9G endorsements."

- name: "9G Order Copy Request"
  path: "BureauOfImmigration/9g-order-copy-request.md"
  reason: "If BI record is needed in documentary form, obtain an official 9G order copy before downstream filings."

- name: "9G Visa Extension"
  path: "BureauOfImmigration/9g-visa-extension.md"
  reason: "Status check may reveal expiry or missing receipts that require an extension or amendment."

- name: "9G Downgrade and I-Card Cancellation"
  path: "BureauOfImmigration/9g-downgrade-and-i-card-cancellation.md"
  reason: "If BI status shows employment ended or OTL required, downgrade and I-Card cancellation services are the next steps."

- name: "9G I-Card Release"
  path: "BureauOfImmigration/9g-i-card-release.md"
  reason: "Status check helps confirm whether an I-Card has been issued and is ready for release."

- name: "9A Visa Extension"
  path: "BureauOfImmigration/9a-visa-extension.md"
  reason: "If status check shows 9A (tourist) record, the client may require a 9A extension rather than 9G-related services."

- name: "13A Visa Progress Inquiry"
  path: "BureauOfImmigration/13a-visa-progress-inquiry.md"
  reason: "Analogous short status-check service for 13A; included for cross-reference when family-based classifications are involved."

