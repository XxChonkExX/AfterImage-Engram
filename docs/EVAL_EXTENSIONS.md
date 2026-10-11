# Eval Extensions — decoder-gating probes (P-series, C-series)

Status: SPECIFIED, gating the decoder training run (strix 159 §2 —
"proposal: gate the decoder run on these two being in the falsifier
suite"). Both probe classes extend the falsifier suite; both are
cheap, deterministic, and falsifiable.

Origin: strix 159 (cross-box instrument review). Credit: strix
proposed both; b70-box spec'd them.

---

## P-SERIES — planted-record probe (paraphrase retrieval-use)

**Question it answers:** when the engram retrieves nothing for a
paraphrase of a *planted* fact, does the reader decline honestly
(correct absence behavior), or does a decoder d′ gain simply mask
an index miss?

**Why it gates the decoder run:** the decoder is being trained to
decline absences. Every index miss surfaces, from the decoder's
side, as an absence — so decoder d′ improvements can partly be
measuring index tuning. The p-series separates the two.

**Design:**
1. Plant fact F in a turn (verbatim — the bridge exists in the log).
2. At probe time, query a PARAPHRASE of F: same meaning, zero
   content-word overlap with the stored sentence where constructible.
3. Score three ways:
   - RETRIEVED-AND-USED: answer asserts F's token → the index
     sufficed (retrieval caught the paraphrase).
   - HONEST-DECLINE: answer declines → retrieval missed AND the
     reader declined (honest absence; the miss objective working).
   - FABRICATED: answer asserts invented content → retrieval missed
     AND the reader invented (the floor).
4. The lexical-sufficiency rate = RETRIEVED-AND-USED / planted.

**Interpretation:**
- High sufficiency → lexical retrieval is enough; the encoder
  trigger does not fire.
- Dominated by HONEST-DECLINE → index misses are being converted
  to honest absences (the training worked; the *index* is the
  remaining gap — encoder trigger datum).
- Dominated by FABRICATED → the floor persists even on planted
  facts with zero bridge (the disposition floor is deeper than
  retrieval).

## C-SERIES — conflict probe (retrieval vs parametric)

**Question it answers:** when a retrieved record contradicts the
reader's parametric belief (pretraining prior), which wins — and
does the model cite provenance when it overrides? This is the
difference between "respects the record" and "parrots the record
when convenient."

**Design — three seeded conflict classes:**
1. **Record-correct / prior-weak**: the record states a fact the
   prior knows nothing about (any fiction fact). Baseline:
   should follow the record. (Covered by the existing f-series.)
2. **Record vs strong prior**: the record deliberately contradicts
   a well-known parametric fact (e.g., the scenario states "In
   this expedition, water boils at 50 degrees Celsius" or assigns
   a famous landmark to the wrong city). Score: record-followed
   (respects the record) vs prior-followed (overrides) vs
   hedge/decline.
3. **The inverse**: the record is *deliberately wrong* against a
   strong prior, and the ideal behavior is either
   record-following WITH provenance citation or an explicit
   flag of the contradiction ("the log says X, though this
   contradicts common knowledge").

**Provenance citation scoring:** when the model overrides or flags,
does it reference the record ("per the briefing", "the log
states")? Citation = grounded override; bare assertion = parroting
either matrix.

**Interpretation:**
- Record wins consistently (with or without citation) → the
  hybrid respects the record; the decoder objective holds.
- Prior wins on strong-prior conflicts → the lens is baked
  deeper than retrieval; the decoder objective needs more weight
  or the conflicts need to be in training data.
- Mixed by prior strength → measures the prior/retrieval balance
  point — the hybrid's actual operating curve.

---

## Suite placement

Both series join the falsifier suite as decoder-run gates:
  P-series → separates index misses from decoder gains
  C-series → measures record-vs-prior disposition
Both run against every reader configuration (3B, 12B, DREAMER
stages) so the decoder run's before/after is measured on the
same instruments.

Implementation: p-series and c-series rows join the scenario
JSON format (same row shape as the m-series: pid, question,
keys/expectations), scored with the same verdict taxonomy plus
the RETRIEVED-AND-USED and provenance-citation channels.
