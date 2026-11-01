---
title: "How to Fill Out a W-9 as a Single-Member LLC, Line by Line"
slug: how-to-fill-out-w9-single-member-llc
description: "Single-member LLC? Your name on line 1, the LLC on line 2, check Individual/sole proprietor, and give your SSN, not the LLC's EIN."
labels: [Starting a Business, Licensing & Registration]
category: licensing-and-registration
status: draft
---

**Short answer:** if you own a single-member LLC that never elected to be taxed as a
corporation, the IRS treats the LLC as part of you. On Form W-9, put **your own name
on line 1** and **the LLC's name on line 2**, check **Individual/sole proprietor** on
line 3a (not the "LLC" box), and enter **your SSN**, or an EIN issued to you
personally. Don't enter the LLC's own EIN. Then sign, date, and give the form to the
client who asked for it. You don't send it to the IRS.

![Form W-9 for a default single-member LLC: line 1 is the owner's name, line 2 the LLC's name, line 3a Individual/sole proprietor, and the TIN is the owner's SSN, never the LLC's EIN](assets/images/w9-single-member-llc-lines.webp "The four entries that matter for a disregarded single-member LLC, from the Form W-9 (Rev. March 2024) instructions.")

This guide covers the current Form W-9 (Rev. March 2024) for a U.S. individual who
owns one LLC. If your LLC has elected S corporation or C corporation tax treatment,
the answers are different; see the S corp and C corp section further down.

# Why clients ask for a W-9 in November and December

A business that pays you has to report certain payments to the IRS on an information
return, usually Form 1099-NEC for services. Form W-9 is how they get your correct
name and taxpayer identification number (TIN) for that return. For 2026, a client who
paid you **$2,000 or more** for services in the course of their business generally
has to send you a 1099-NEC by **February 1, 2027** (January 31 falls on a Sunday).
That's why W-9 requests pile up at the end of the year.

If you're on the other side, paying contractors, read
[[do-i-need-to-send-1099-to-llc|do I need to send a 1099 to an LLC?]] It explains
how to read the W-9 you get back.

# First: is your LLC "disregarded"?

An LLC is a state legal entity. For federal income tax, the IRS classifies it by
the number of owners and any election it made:

- **One owner, no election:** the LLC is a *disregarded entity*. Its income goes on
  your own return (Schedule C, E, or F), the same way as a sole proprietorship.
- **One owner that filed Form 8832 or Form 2553:** the LLC is taxed as a C or S
  corporation.
- **Two or more owners, no election:** the LLC is taxed as a partnership.

If your LLC never filed Form 8832 or Form 2553, it's almost certainly in the first
group, and everything below applies.

# Filling it out, line by line

| W-9 line | What a disregarded single-member LLC enters |
|---|---|
| 1. Name of entity/individual | Your own name, as shown on your income tax return |
| 2. Business name/disregarded entity name | The LLC's name |
| 3a. Federal tax classification | Individual/sole proprietor |
| 3b. Foreign partners box | Leave blank |
| 4. Exemptions | Usually blank |
| 5–6. Address | Where you want your 1099 mailed |
| 7. Account numbers | Optional |
| Part I. TIN | Your SSN, or an EIN issued to you personally |
| Part II. Certification | Your signature and the date |

**Line 1: your name, not the LLC's.** The instructions say a disregarded entity
enters "the owner's name on line 1" and that this name "should never be a disregarded
entity." It's the name on the tax return where the income is reported, which for you
is your Form 1040.

**Line 2: the LLC's name.** This is the "disregarded entity name" line. If you also
use a trade name (DBA), the instructions put business, trade, DBA, and disregarded
entity names on this line too.

**Line 3a: check Individual/sole proprietor.** This is the step people most often get
wrong. The form itself says a disregarded entity "should instead check the
appropriate box for the tax classification of its owner." You're an individual, so
you check **Individual/sole proprietor**. The "LLC" box is for LLCs taxed as a
partnership or a corporation, and it needs a code: C, S, or P. There's no code for a disregarded LLC. The
March 2024 revision changed this line so that point is spelled out on the form.

**Line 3b: leave it blank.** It applies only to partnerships, trusts, and estates with
foreign partners, owners, or beneficiaries.

**Line 4: usually blank.** The instructions say individuals, including sole
proprietors, generally aren't exempt from backup withholding, so there's no exempt
payee code for you. The FATCA code only matters for accounts held outside the
United States.

**Lines 5 and 6: your address.** The requester uses it to mail your information
returns. If it's different from the one they have on file, the instructions say to
write "NEW" at the top.

**Part I: your SSN, or an EIN in your own name.** For a single-member LLC that's
disregarded, the instructions say to "enter the owner's SSN (or EIN, if the owner
has one)." The IRS page on single-member LLCs puts it more directly: the W-9 "should
provide the owner's SSN or EIN, not the LLC's EIN." The form's name-and-number chart
adds that the IRS encourages sole proprietors and owners of disregarded entities to
use their SSN.

**Part II: sign and date.** For a disregarded entity, the person on line 1 signs.
That's you, the owner.

# "But my LLC has its own EIN"

Many single-member LLCs do. The IRS says a disregarded LLC needs its own EIN if it has
employees or owes certain excise taxes. It can also get one if a bank or state tax law
requires it. Having the number doesn't change your income tax classification. The
LLC's EIN is for **payroll and those excise taxes**. For W-9s and anything else tied
to income tax reporting, the IRS says to use the owner's SSN or EIN.

If you're still sorting out which numbers your business needs,
[[ein-number-free|what an EIN is and how to get one for free]] walks through it.

The name line and the number line have to belong to the same taxpayer. The W-9 says
"the TIN provided must match the name given on line 1 to avoid backup withholding."
"Doe Design LLC" with your SSN, or "Jane Doe" with the LLC's EIN, is the kind of
pairing that rule is meant to catch.

![Comparison of W-9 entries for a single-member LLC with no election, an LLC taxed as an S or C corporation, and a multi-member LLC taxed as a partnership](assets/images/w9-llc-name-number-table.webp "Who goes on line 1 and whose number goes in Part I changes with the LLC's tax classification. Source: Form W-9 (Rev. March 2024).")

# If your LLC elected S corp or C corp tax treatment

Once an LLC files Form 2553 or Form 8832 to be taxed as a corporation, it is the
taxpayer, so the W-9 changes:

- **Line 1:** the LLC's name, as shown on its own tax return.
- **Line 2:** any trade name or DBA, if different.
- **Line 3a:** check **LLC** and write **S** or **C** in the space.
- **Part I:** the LLC's EIN.

Line 4 exemption codes can apply to corporations, but the chart in the instructions
limits them by payment type, and S corporations have narrower exemptions. Read it
before entering a code. If the name or TIN on your account changes later (an S
election, for example, means the LLC's EIN replaces your SSN), the instructions say
to furnish a new W-9.

An S or C election has consequences well beyond the W-9, so get advice before you
make one. The state side of keeping an LLC is covered in
[[llc-cost-breakdown|what an LLC really costs]].

# Mistakes that cost you money

**Not sending it back.** If you don't furnish your TIN, your payments become subject
to backup withholding: the payer keeps 24% and pays it to the IRS. The
W-9 also lists a $50 penalty for each failure to furnish a correct TIN unless there's
reasonable cause.

**A name and number that don't match.** If the IRS tells your client the TIN you gave
is incorrect, your payments can become subject to backup withholding too.

**Guessing when you're not sure.** The form carries a civil penalty of $500 for a
false statement with no reasonable basis that results in no backup withholding.
Willfully falsifying the certification can lead to criminal penalties.

**Sending your SSN carelessly.** A completed W-9 has your SSN on it. Give it only to
the business that is actually paying you, ideally through their vendor portal or
another secure channel rather than a plain email attachment. The W-9's own identity
theft section warns that the IRS doesn't start contact with taxpayers by email. A
"W-9 request" that claims to come from the IRS is a red flag.

# A note on the 2026 draft form

The IRS has posted an early draft of a new revision, **Form W-9 (Rev. June 2026)**,
marked "DRAFT, NOT FOR FILING." As of November 2, 2026, the IRS's About Form W-9
page still lists the March 2024 form as the current revision. The draft doesn't
change the single-member LLC answer. It states it more bluntly: "Do not enter the
EIN of a disregarded entity." If a client sends you a newer revision after it's
final, fill it out the same way.

# Quick checklist

| Before you send it | Check |
|---|---|
| Line 1 | Your own legal name, matching your Form 1040 |
| Line 2 | The LLC's exact name |
| Line 3a | Individual/sole proprietor checked, LLC box empty |
| Part I | Your SSN or personal EIN, not the LLC's EIN |
| Address | Where you want the 1099 to arrive |
| Signature | Signed and dated by you |
| Delivery | Sent to the client, never to the IRS |

# Where these answers come from

| Source | What it establishes |
|---|---|
| [IRS — Form W-9 (Rev. March 2024)](https://www.irs.gov/pub/irs-pdf/fw9.pdf) | line 1 and 2 rules for disregarded entities; line 3a "check the box for the owner"; line 3b and 4 instructions; "NEW" address rule; SSN or owner's EIN in Part I; TIN must match line 1; the person on line 1 signs; 24% backup withholding and its triggers; $50 and $500 penalties; new W-9 when name or TIN changes; "Do not send to the IRS"; the IRS doesn't start contact by email |
| [IRS — About Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) | March 2024 is the current revision (checked November 2, 2026) |
| [IRS — Draft Form W-9 (Rev. June 2026)](https://www.irs.gov/pub/irs-dft/fw9--dft.pdf) | the draft revision and its "do not enter the EIN of a disregarded entity" wording |
| [IRS — Single member limited liability companies](https://www.irs.gov/businesses/small-businesses-self-employed/single-member-limited-liability-companies) | default classification and Form 8832; W-9 uses the owner's SSN or EIN, not the LLC's EIN; when a disregarded LLC needs its own EIN |
| [IRS — Instructions for Forms 1099-MISC and 1099-NEC (12/2026)](https://www.irs.gov/instructions/i1099mec) | the $2,000 threshold for 2026 payments; the January 31 due date and next-business-day rule; trade or business payments only |

This is general information about federal tax forms, not tax or legal advice for your
situation. The IRS pages above are the authority. States can have their own vendor
forms and rules, which this guide doesn't cover.
