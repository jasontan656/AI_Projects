---
aliases:
- AEP check
categories:
- solo_task
department: DepartmentOfLabor
name: AEP Checking
slug: aep-checking
type: solo_task
updated_at: '2025-10-17'
---

# AEP Checking

## Summary

AEP Checking is a short, focused verification service to confirm the authenticity, validity, and recorded details of an employer-issued DOLE Alien Employment Permit (AEP) for a named beneficiary. Typical customers are employers, HR teams, immigration agents, or foreign employees who need rapid confirmation that an AEP card or AEP record matches DOLE records and is suitable as input for downstream immigration filings (for example 9G BI applications). The service performs a payment-confirmed check and delivers a short AEP Verification Report that records which fields were checked and any discrepancies found.

---

## Background prerequisites

Customers must meet the following preconditions to request AEP Checking:

- Geographic prerequisite: Remote checks are possible for initial screening (using scanned copies) but in-person verification at DOLE or handling of original AEP cards may be required for definitive confirmation in some cases.
- Relationship prerequisite: The requester must be the employer, the named AEP beneficiary, or an authorised representative with a signed authorization letter accepted by DOLE or by our office.
- Business prerequisite: The client must provide identifying details (applicant full name, passport number, employer name) and at least one of the following: a scanned image of the AEP card, a DOLE reference number, or a copy of the AEP application receipt.

Not eligible:
- Cases where no identifying AEP details can be provided (for example no name, no passport number, and no scanned proof). In such cases the check cannot proceed.
- Requests that require DOLE to reissue or change an AEP — this verification service only checks and reports; it does not perform cancellations or reissuance.

---

## Required documents

### Documents the client must provide (cannot be produced by this service)

- AEP card image or scan (if available):
  - Type: copy/scan × 1
  - Requirements: Clear scan or photo of the AEP plastic card (front and back) or the DOLE-issued reference document. Used to verify printed details versus DOLE records.

- Beneficiary identification:
  - Passport bio page (scan) × 1 — used to match the AEP record to the passport number and name.

- Employer identification:
  - Company name and basic identifier (SEC/DTI number or employer TIN) × 1 — used to cross-check sponsor details.

If the client lacks the AEP card scan but has a DOLE reference number or DOLE submission receipt, provide that receipt instead.

---

## Documents the service can produce

- AEP Verification Report:
  - document: "AEP Verification Report"
  - producer: "AEP Checking"
  - path: "DepartmentOfLabor/aep-checking.md"
  - Usage: One-page report summarising the verification results: matched fields, mismatches, DOLE-record status snapshot (if DOLE query permitted), and recommended next steps.

- Advisory note for follow-up actions:
  - document: "AEP Check Advisory"
  - producer: "AEP Checking"
  - Usage: Recommends remediation steps when discrepancies are found (for example: request AEP Card Release, file Affidavit of Loss, request AEP Cancellation, or initiate AEP amendment request).

---

## Outcome / Deliverables

After completion the client will receive:

- AEP Verification Report (PDF): confirms whether the supplied AEP data matches accessible DOLE references and lists any discrepancies found.
- A short advisory with recommended next steps if any inconsistency is detected (for example request a certified AEP copy, proceed to AEP Cancellation, or escalate to DOLE liaison).

Retention: Clients should keep the AEP Verification Report with their immigration case file and provide it to downstream teams (for example BI 9G filing teams) as evidence of pre-filing verification.

---

## Process / Steps

**Total estimated duration:** Typically same-day to 2 business days depending on the evidence provided and whether an on-site DOLE lookup is necessary.

### Step 1: Intake and payment confirmation

**Estimated duration:** same-day

Specific actions:
1. Client provides the required inputs (AEP scan or DOLE receipt, passport bio page, employer identification).
2. Confirm and collect the AEP Checking service fee (pre-payment is required before verification begins).

**Required items:** AEP scan or DOLE receipt; passport scan; employer name and identifier; payment confirmation.

**Notes:** The service requires payment before starting. Common practice documented in chat evidence shows a small standard checking fee historically used by operators.

---

### Step 2: Verification (remote)

**Estimated duration:** same-day to 1 business day

Specific actions:
1. Match the supplied AEP card details to the passport number and beneficiary name.
2. If a DOLE reference or receipt is supplied, query internal DOLE contact channels or industry knowledge sources (where permitted) to confirm record existence and basic metadata (issue date, employment period, employer name).
3. Record any mismatches (for example name spelling differences, employer mismatch, card expiry or incorrect employment period) in a working note.

**Completion sign:** A working verification status (matched / partially matched / no match) recorded; proceed to Step 3.

---

### Step 3: On-site or authoritative lookup (conditional)

**Estimated duration:** 1–2 business days (only if required and authorised by client)

Specific actions:
1. With client authorization, perform an authoritative lookup with DOLE or the document holder (for example request AEP Card Release status or record confirmation) when remote evidence is insufficient.
2. Where DOLE requires original documents or formal authorisation to reveal records, instruct client on the required authorisation or obtain the signed release for the lookup.

**Completion sign:** DOLE-provided confirmation or a clear statement of inability to confirm (for example no record found). This authoritative result is included in the final report.

---

### Step 4: Deliver final report and advisory

**Estimated duration:** same-day after verification completes

Specific actions:
1. Produce the AEP Verification Report summarising checked fields, authoritative confirmations, and recommended next steps.
2. Deliver the report to the client and, if requested, an advisory note outlining the remediation options and estimated costs/timelines for follow-up services.

**Completion sign:** Client acknowledges receipt of the report. If discrepancies require action, client may commission follow-up services (AEP Card Release, Affidavit of Loss, AEP Cancellation, AEP Amendment).

---

## Price & Fees

| Effective Date | Currency | Amount | Applicable Conditions | Notes | Evidence |
| -------------- | -------- | ------:| -------------------- | ----- | -------: |
| 2022-09 | PHP | 500 | Per-check fee historically charged for AEP checking | Standard small checking fee recorded in chat evidence; agent practice: request payment before running the check | messages 223637, 260477 |

**Price notes:**
- The PHP 500 figure is recorded in chat evidence as the recurring small checking fee historically requested by operational teams. Confirm current fee at intake.
- The fee covers the remote verification and short report. On-site DOLE lookup, couriering originals, or liaison services are billed separately.

---

## Important notes / Risks

### Limitations
- This service verifies AEP information against available references and performs limited authoritative lookups when authorised. It does not substitute for formal DOLE re-issuance, cancellation or amendment processes.
- DOLE may refuse to disclose some record details unless authorised by the employer or the cardholder; in such cases the report will record the limitation and advise next steps.

### Time sensitivity
- Perform AEP Checking early in the 9G/BI filing chain: discovering mismatches before filing avoids rejected BI submissions and extra costs.

### Risk warnings
- If a supplied AEP card is counterfeit or manipulated, the check will flag inconsistencies and recommend escalation (for example request DOLE-certified copy or advise cancellation and re-application). Do not attempt to use suspected counterfeit documents in formal filings.

---

## Frequently Asked Questions

Q: What do you check in an AEP check?
A: We confirm the visible card fields against the passport number and the employer name, and (if authorised) query DOLE or internal channels for record existence and basic metadata (issue date, employment period).

Q: How long does the check take?
A: Typically same day when clear scans are provided. On-site or DOLE-authoritative lookups may take 1–2 additional business days.

Q: What if you find a mismatch?
A: We issue a Verification Report describing the discrepancy and recommend next steps (for example request AEP Card Release, file an Affidavit of Loss, initiate AEP Cancellation or AEP amendment services).

---

## Evidence sources

- Message 223637 (2022-09-12): Requesting 500 pesos for AEP checking of MO GUOFAN. (D:\AI_Projects\.TelegramChatHistory\Organized\groups\All Directions Cashier_392395182.jsonl)
- Message 260477 (2022-10-18): Requesting 500 pesos for ZHU GUIBING AEP checking. (D:\AI_Projects\.TelegramChatHistory\Organized\groups\All Directions Cashier_392395182.jsonl)

Data extraction timestamp: 2025-10-17 21:52:47

---

## Related businesses

- name: "AEP Application"
  path: "DepartmentOfLabor/aep-application.md"
  reason: "Produces the AEP card that is commonly verified by this checking service."

- name: "AEP Card Release"
  path: "DepartmentOfLabor/aep-card-release.md"
  reason: "If the AEP exists but the physical card needs collection, use the card release service."

- name: "Affidavit of Loss (AEP)"
  path: "DepartmentOfLabor/affidavit-of-loss-for-aep.md"
  reason: "If the AEP card cannot be located, the affidavit of loss is a common prerequisite for replacement or cancellation."

- name: "AEP Cancellation"
  path: "DepartmentOfLabor/aep-cancellation.md"
  reason: "If verification reveals an invalid or compromised AEP, cancellation may be required."

---

## Document information
- Source file: D:\AI_Projects\\.TelegramChatHistory\\KB\\services\\aep-checking.md
- Integration date: 2025-10-17
- Evidence messages referenced: 223637, 260477
