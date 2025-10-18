---
aliases:
- tax card
- BIR tax card
categories:
- solo_task
department: BureauOfInternalRevenue
name: Tax Card Application
slug: tax-card-application
type: solo_task
updated_at: '2025-10-17'
---

# Tax Card Application

## Summary

Tax Card Application is a standalone service to assist a client in obtaining an official tax card/registration (BIR-related identification or tax registration document) needed for employment, payroll and tax compliance in the Philippines. Typical users are foreign employees or their employer HR teams who require an authentic tax card (or BIR registration evidence) for payroll withholding, AEP application support, or other government filings. The service prepares required paperwork, submits the application to the Bureau of Internal Revenue (or the relevant local tax office), follows up until issuance, and returns the official evidence to the client.

This entry was created based on a client case: Gina requires both an AEP card and a valid tax card. The AEP and tax card processes are operationally related in this case but remain separate solo tasks.

---

## Background prerequisites

Customers must meet the following conditions to request this service:

- Geographic prerequisite: The applicant or an authorized local representative must be in the Philippines for in-person submission or collection when the tax office requires originals. Remote advisory and document preparation is possible but final steps often require local presence.
- Relationship prerequisite: The requester should be the taxpayer (employee) or an authorized employer/HR representative who can lawfully submit tax registration documents on the employee's behalf.
- Business prerequisite: The client must have a valid passport and supporting employment evidence if the tax card is linked to employment status (for example employer letter, contract). If the tax card requires documentary verification (for example proof of residence, birth certificate), those must be supplied by the client.

Not eligible:
- Cases where the client cannot provide minimum identity information or cannot arrange local representation where originals are required.

---

## Documents required (must be provided by client)

The following items must be supplied by the client and cannot be produced by this service.

**Passport (original or certified copy):**
- Type: original × 1 (or certified copy for intake) 
- Requirement: Valid passport to verify identity. The passport may be temporarily presented to the tax office during processing and returned upon release.
- How used: Identity verification and to link the tax card to the correct person.

**Proof of employment / employer letter:**
- Type: copy × 1
- Requirement: Employer letter or employment contract stating employment relationship, employer tax identification, and purpose of tax card registration. Required when the tax card issuance is tied to payroll or employer withholding obligations.
- How used: Submitted as supporting evidence for tax registration.

**Other identification / address evidence (if requested):**
- Type: original or copy × as required
- Requirement: local address proof or other ID as requested by BIR/local tax office.
- How used: Support identity and contact information on the tax registration.

**Note on originals:** Some local tax offices require originals for inspection and may hold them briefly; clients should expect temporary custody in such cases.

---

## Documents the service can produce

- Tax registration submission packet (completed forms, cover letter, checklist)
  - Producer: Tax Card Application
  - Path: BureauOfInternalRevenue/tax-card-application.md
  - Usage: Ready-to-submit materials to the local BIR office.

- Payment evidence and official receipt package (scanned)
  - Producer: Tax Card Application
  - Usage: Consolidated proof to attach to the client case file and to downstream processes that require tax registration evidence.

---

## Documents obtained after completion

**Tax Card / BIR registration evidence:**
- Type: original or official certified copy × 1
- Can be used for: employer payroll filings, AEP/Bureau of Immigration inputs, proof of tax registration for formal employment processes.
- Retention: Keep the original or certified copy safe for future compliance and immigration filings.

---

## Process / Steps

**Total estimated duration:** Usually 1–3 weeks depending on local tax office workload and whether additional documentation or clarifications are required.

### Step 1: Intake and document collection

**Estimated duration:** 1–2 business days

1. Collect passport copy, employer letter, and any other supporting documents from the client.
2. Verify ID details and ensure all required fields for the tax registration form are complete.

**Needed documents:** passport, employer letter

**Notes:** If a client lacks any supporting document, advise and either pause the application or arrange the auxiliary service needed to obtain the document.

### Step 2: Prepare and submit registration packet

**Estimated duration:** 1–3 business days

1. Complete the BIR/tax office registration forms and attach the employer letter and passport copy.
2. Submit the packet to the local BIR office or the designated collection point and pay any official registration fees as required.
3. Obtain and record the office submission receipt and reference number.

**Completion sign:** Tax office issues a submission receipt or a temporary acknowledgement number.

### Step 3: Follow up and collect tax card or proof

**Estimated duration:** Variable (days to weeks)

1. Monitor the case using the submission reference and respond promptly if the tax office requests additional information.
2. When the tax card or registration evidence is issued, collect the original or certified copy and deliver it to the client.

**Completion sign:** Client receives the tax card / official registration evidence.

---

## Price & Fees

No fixed agent fee is recorded in the source evidence for this generic tax card service. Official registration fees charged by the Bureau of Internal Revenue (or local tax office) apply and are payable in addition to any agent handling fees. Agent handling fees vary by scope (document collection, courier, liaison) and will be quoted at intake.

**Operational note from the source case:** The client in the source chat (Gina) will provide original documents that the agent may collect and may be marked as "collected and not returned" for the processing period — confirm custody expectations at intake.

---

## Important notes / Restrictions

### Document custody and timing
- The tax office may temporarily hold originals during processing; clients should not plan travel that requires those originals until they are returned.

### Relationship to AEP processing
- In the Gina case the tax card and AEP card are being processed together. The tax card evidence may be required by employers or by DOLE/BI workflows. However, the tax card and AEP are independent legal processes and must each satisfy their respective agency requirements.

### Risk warnings
- Using false or misrepresented documents in tax registration can lead to denial or legal consequences. Ensure all supplied documents are authentic and truthful.

---

## Evidence sources

> The following lines are extracted from the source chat evidence that prompted this case entry.

**Message 250207 (2022-10-06):** Elena indicated that Gina needs real AEP card and tax card application assistance. (source: D:\AI_Projects\\.TelegramChatHistory\\Organized\\dialogs\\Elena Wang_771833686.jsonl)

**Message 250213 (2022-10-06):** Jason confirmed Gina requires actual AEP and tax card handling. (same source file)

Data source path: D:\AI_Projects\\.TelegramChatHistory\\KB\\services\\aep卡和税卡办理.md
Extraction timestamp: 2025-10-17 16:28:55

---

## Related businesses

- name: "AEP Application"
  path: "DepartmentOfLabor/aep-application.md"
  reason: "The AEP produced by DOLE is an upstream input in the Gina case; employers commonly require tax registration evidence and AEP in tandem."

- name: "AEP Card Release"
  path: "DepartmentOfLabor/aep-card-release.md"
  reason: "When an AEP card is issued its physical handover is handled by that service; tax registration evidence is often provided alongside AEP for employer records."

---

## Document information
- Source file: aep卡和税卡办理.md
- Integration date: 2025-10-17
- Evidence messages referenced: 250207, 250213
