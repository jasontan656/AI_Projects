---
aliases:
- Accounting Service Payment
categories:
- solo_task
department: BureauOfInternalRevenue
name: Accounting FS Service Payment
slug: accounting-fs-service-payment
type: solo_task
updated_at: 2025-10-17
---

# Accounting FS Service Payment

## Summary

Accounting FS Service Payment records the steps and requirements to pay the deposit or advance required to start an Accounting Financial Statement (FS) preparation service. Typical clients are corporate finance representatives, company owners, or authorised agents who must submit a deposit to a specified BDO bank account before the accounting team starts work on preparing a financial statement, audited FS, or related accounting deliverables.

This solo task documents required payment information, the evidence clients must provide, the agent confirmation workflow, and related downstream services that consume the completed financial statement.

---

## Background prerequisites

Customers must meet the following conditions to complete this payment task:

- Geographic prerequisite: Payment can be made remotely by bank transfer (BDO account) or in-person deposit. The payer must have the ability to transfer funds or deposit cash to the specified account.
- Relationship prerequisite: Payer must be the company authorised signatory, CFO, or a duly authorised representative with written authority to make payments on behalf of the company.
- Business prerequisite: The deposit is required to reserve work for Accounting FS preparation. The service will not commence until proof of deposit is confirmed and recorded.

Not eligible:
- Anonymous payments with no payment reference or where the payer cannot provide verifiable payment proof.

---

## Required documents and information

### Documents / evidence the client must provide (must be supplied by the payer)

1. Payment proof
- Type: bank transfer screenshot or scanned deposit slip
- Requirements: must show payer name, exact amount, date/time, beneficiary account name and account number, and the transaction reference. If intermediary fees were deducted, provide evidence of the net amount and the payer's instruction showing the gross amount intended so the agent can reconcile.
- Use: The agent attaches this proof to the accounting case file and issues a payment confirmation to the accounting team.

2. Payment reference information
- Type: text
- Requirement: The payer must include the case reference or invoice number in the payment reference field (for example the Accounting FS case number or client invoice ID) to enable automatic reconciliation.

3. Payer identity and authorisation (if applicable)
- Type: scanned ID and a signed authorisation letter when a third party pays on behalf of the company.
- Use: Verifies authority to make the payment and enables the agent to accept the payment on behalf of the accounting provider.

### Documents the service can produce

- Payment Confirmation (producer: Accounting FS Service Payment)
  - document: payment_confirmation_${YYYYMMDD}_${client}.pdf
  - usage: Agent-issued confirmation that records the deposit amount, payer identity, beneficiary account, transaction reference and timestamp. This confirmation is attached to the accounting engagement and used as proof that work may commence.

---

## Process / Steps

**Total estimated duration:** Typically same-day for bank transfer confirmation; allow 1 business day for reconciliation if intermediary fees or queries arise.

### Step 1: Prepare payment instruction (client)

**Estimated duration:** minutes

1. Obtain the banking details from the accounting provider (beneficiary name, BDO account number, branch if required, and the exact amount to deposit).
2. Include the specified case reference or invoice number in the payment reference field when making the transfer. If the payer is a third party, ensure the authorisation letter is signed and available.

**Notes:** Use the exact beneficiary name and account number provided by the accounting provider to avoid misdirected funds.

### Step 2: Execute payment

**Estimated duration:** immediate to same day

1. Make the BDO deposit or bank transfer following the instruction. Keep a clear screenshot or the physical deposit slip.
2. If paying from an overseas bank, ensure the payer covers intermediary fees or instructs transfer net/gross per the provider's reconciliation preference.

**Required evidence:** bank screenshot or scanned deposit slip with transaction reference.

### Step 3: Upload or send payment proof to the accounting provider

**Estimated duration:** same day

1. Send the payment proof to the accounting engagement contact (email or secure upload channel) and include the case reference and payer contact details.
2. If a third-party made the payment, include the signed authorisation and payer ID.

**Completion sign:** Provider acknowledges receipt of the proof and issues an internal payment confirmation.

### Step 4: Provider issues Payment Confirmation and starts engagement

**Estimated duration:** same day to 1 business day

1. Provider reconciles the payment to the invoice or case reference. If there is a mismatch (amount or missing reference), provider requests clarification and the payer resolves the discrepancy.
2. Once reconciled, provider issues the Payment Confirmation PDF to the payer and to the internal accounting engagement team.
3. The Accounting FS preparation work is scheduled to start per provider lead times.

**Completion sign:** Payment confirmation delivered and the accounting engagement moves from "awaiting deposit" to "in progress." 

---

## Price & Fees

| Effective Date | Currency | Amount | Applicable Conditions | Notes | Evidence |
|---------------:|:--------:|------:|----------------------|------:|---------:|
| 2025-03-12 | PHP | 10,000 | Deposit required to start Accounting FS service | Deposit amount recorded in chat evidence as required to begin accounting FS work; confirm amount at intake | Message 1169 (2025-03-12) |

**Price notes:**
- The PHP 10,000 figure is the recorded deposit in the evidence. Final service prices include the accounting provider's fee for the preparation of financial statements; the deposit is an advance to secure work and may be applied against the total invoice.
- Confirm the full contract price and refund / cancellation policy at engagement intake.

---

## Attention & Risk Warnings

- Use the correct beneficiary BDO account number and include the exact case/invoice reference. Missing or incorrect references delay reconciliation.
- If paying from an overseas bank account, intermediary and FX fees may reduce the net amount received. Specify whether the payer or the recipient bears such fees; provide proof of gross payment if needed to reconcile.
- Provider will not start substantive accounting work until payment is reconciled. Keep original deposit receipts until the provider confirms the payment and work start.

---

## Frequently Asked Questions

Q: What if I already paid but used the wrong payment reference? 
A: Send proof of payment immediately to the accounting provider and explain the error. The provider will reconcile by payer name and transaction reference, but resolution may take 1 business day.

Q: Is the deposit refundable if I cancel? 
A: Refund policies vary by provider. Confirm refund and cancellation terms in the engagement agreement before paying the deposit.

Q: Can I pay by other channels besides BDO transfer? 
A: Check with the accounting provider. They may accept other bank transfers, GCash, or cashier payments but the instruction above records a BDO deposit in the evidence.

---

## Evidence sources

Message 1169 (2025-03-12): Deposit 10k to BDO account for accounting FS service.

Data source file: D:\AI_Projects\\.TelegramChatHistory\\Organized\\unknown\\All Directions Cashier new_2136036788.jsonl
Extraction timestamp: 2025-10-18 04:47:38

---

## Related businesses

- name: Annual Financial Statement Preparation
  path: BureauOfInternalRevenue/annual-financial-statement-preparation.md
  reason: Accounting FS deposit is the starting payment that enables the Annual Financial Statement Preparation service to begin work.

- name: 1702RT Filing
  path: BureauOfInternalRevenue/1702rt-filing.md
  reason: The prepared financial statements produced by the accounting engagement are commonly attached to the 1702RT filing as required by BIR.

---

## Document information
- Source file: D:\AI_Projects\\.TelegramChatHistory\\KB\\services\\accounting-fs-service-payment.md
- Integration date: 2025-10-17
- Evidence messages referenced: 1169
