# BUG-03: retrospective

## Summary
- **Root cause:** invoice status was never modelled as a type. Eight domain concepts got
  StrEnums; the field the entire scoring pipeline pivots on did not, so five sites each
  declared their own literal and the CSV path invented a sixth word.
- **Fix approach:** `InvoiceStatus(StrEnum)` with the already-persisted values, routed through
  all five sites; corrected the diagnostic that misattributed the failure.
- **Classification:** Data / S1-High / Design / Incorrect
- **Outcome: PARTIAL.** The status defect is fixed. The scenario is still not scorable for a
  second, deeper reason — escalated as BUG-06, recorded as a strict xfail.

## Process Improvement

**Prevention:** the column was `Mapped[str] = mapped_column(String(20))` with no constraint,
and there was no enum to bind. A domain value with a closed set of legal values needs a type
at the point of definition — otherwise every writer is correct by construction and drift is
undetectable until a reader disagrees. The generated path worked only because two literals
happened to match two other literals; nothing enforced it.

**Pattern:** `Origin=Design` + a bare `str` column holding a closed vocabulary → the bug is not
in the wrong value, it is in the absence of the type. Fixing the literal alone leaves the next
writer equally free to invent a seventh word. This is BUG-02's root cause one stage earlier:
there, an enum existed and a hand-written copy drifted from it; here, the enum was never
created, so there was nothing to drift *from*.

## Two things this bug taught that the error message actively prevented

1. **The diagnostic was lying.** `InsufficientOutstandingError` said *"Every invoice in this
   scenario is settled"* when in fact none were settled — they carried a status matching
   neither branch. The message encoded the assumption that zero outstanding implies full
   settlement, which sends the reader to the payments logic, several layers from the defect.
   It cost real time on this investigation before the reproduction contradicted it. Now fixed
   to report observed status counts and name unrecognised values.

2. **A partition on equality is not a partition.** The extractor computes
   `status == "overdue"` and `status == "paid"` as two independent masks. A third value is not
   an error — it silently belongs to neither, and the data simply disappears. Any code that
   splits a domain into cases by equality should either be exhaustive over an enum or have an
   explicit else-branch that raises. Silent set subtraction is how 30 invoices vanished.

## Why it was never caught

`tests/test_csv_upload.py` had four tests and all four asserted on the *upload response*:
201 on valid input, 422 on three kinds of bad input. None asked whether the persisted scenario
could subsequently be used. The CSV feature was verified up to the instant of writing and not
one step further, so the defect lived entirely in the gap between "it saved" and "it works" —
a gap no test spanned. The new roundtrip test spans it.

This is a third distinct instance of the same testing failure this session:
BUG-01 (a gate nobody ran), BUG-02 (a loop that asserted nothing when empty), BUG-03 (a
feature tested up to persistence only). All three are the same shape — **the test observes a
proxy for the outcome rather than the outcome.**

## Escalated: BUG-06 — uploaded scenarios cannot be supervised-trained

Recorded as `@pytest.mark.xfail(strict=True)` so the criterion is not silently dropped and the
suite will fail loudly the moment it is resolved.

`create_from_csv` sets `payment_history_pattern=PaymentPattern.ON_TIME` for every client,
because a CSV of receivables carries no payment history. `OutcomeLabeller` simulates the
outcome from exactly that field — `PATTERN_PROFILES[pattern].late_days_mean` feeding an
exponential draw — so every client gets the same distribution, every label comes out 1, and
`build_training_set` aborts with a single-label-class error.

**This is not fixable by assigning varied patterns.** Deriving the pattern from observable
ageing would make the label a deterministic function of `days_overdue`, which is a feature —
precisely the leakage ADR-006 declares non-negotiable. Assigning them at random would make the
model train successfully on noise, which is worse than failing: it would produce confident
scores that mean nothing.

The real question is architectural: ADR-006's design trains per-scenario on labels simulated
from a hidden generative `_PatternProfile` that only synthetic data possesses. Uploaded data
has no such truth. Scoring unlabelled data is what a *pre-trained* model is for. That is an
ADR-level decision and belongs to the team, not to this bugfix.

## Heutagogical Checkpoint

1. **Learned:** the scoring pipeline's dependency on `payment_history_pattern` runs deeper than
   the ADR-006 leakage guard suggests. The guard keeps it out of the *features*; the labeller
   depends on it entirely. That makes the whole supervised approach specific to generated data,
   which is a constraint on the product (CSV upload is B-07/RF-07, a shipped feature) that is
   not written down anywhere I found.
2. **Process change:** read the error message, then verify it against the data before believing
   it. "Every invoice is settled" was a confident, specific, wrong claim.
3. **Framework improvement:** a check for `Mapped[str]` columns holding closed vocabularies
   with no corresponding enum would have caught this at the model layer. More generally, the
   three concealment shapes found today all evade the "all tests pass" gate, which suggests
   gate coverage is being measured by suite greenness rather than by what the suite observes.
4. **Capability gained:** can recognise the "tested up to persistence" gap — where every
   assertion is about the write and none about the read.

## Patterns
- **Added: none** — `rai pattern add` is a silent no-op (BUG-01 retro). Preserved here:
  - A closed vocabulary in a bare `str` column is a missing type, not a missing check.
  - Splitting a domain by equality masks silently drops values matching no case; be exhaustive
    over an enum or raise on the else.
  - An error message is a hypothesis, not evidence. Verify it against the data.
