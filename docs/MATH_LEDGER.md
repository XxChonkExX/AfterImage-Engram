# Math Ledger — the portable core

Every method here is a pure function of text and counters: no
weights, no model identity, no embedded data. These are the engram's
universal wire interface — the same lines of math run on any domain,
any reader, any box. (The store is instance; the math is the
machine.)

Each entry: the measured problem it attacks, the formulae, the
mapping into Afterimage, and what falsifies it.

---

## M1. Signal Detection Theory — the disposition, quantified
**Attacks:** the measured fact that small-model readers cannot
distinguish known from absent (fabrication rates 73–100%, and
discriminability d′ measured *negative* across configurations).

    d' = z(H) - z(FA)          sensitivity (knowledge)
    c  = -0.5 (z(H) + z(FA))   criterion (disposition)

H = hit rate on planted facts; FA = false-alarm rate on absent
content; z = inverse normal CDF.

**Mapping:** H from recall probes; FA from the miss taxonomy
(assertions on absent content). The decomposition separates *what
the reader knows* (d′) from *what the reader does* (c) — which is
the prerequisite for measuring any memory or training intervention
without confusing the two.

**Measured:** d′ −0.03 to −4.4 (negative = fabrication rate
exceeds recall rate), criterion strongly liberal. The
before-number for any abstention-training objective.

**Falsifier:** if d′ and c do not separate the absent/planted
tiers, the mapping is wrong.

Related: Semantic Entropy Probes (arXiv 2406.15927) — the
supervised descendant of hand-rolled failure directions.

## M2. Conformal Prediction — absence with a certificate
**Attacks:** hand-picked retrieval thresholds.
Formulae (Vovk et al., distribution-free):

    a_hat = the ceil((n+1)(1-eps))/n quantile of calibration
            nonconformity scores
    guarantee: P(correct | not abstained) >= 1 - eps

**Mapping:** the retrieval overlap score is the natural
nonconformity score; calibrate on known-absent (miss) and
known-present (anchor) probes. The typed-absence threshold becomes
*calibrated* rather than hand-picked.

**Falsifier:** held-out coverage below 1−ε means the score does
not separate presence from absence — try alternative scores
(answer length, hedge markers).

## M3. Survival Analysis — retention with censoring
**Attacks:** naive decay fits that discard unprobed facts and
collapse to single-point estimates.

    Kaplan-Meier: S_hat(t) = PROD (1 - d_i/n_i)
    Weibull hazard: h(t) = (k/lambda)(t/lambda)^(k-1)

**Mapping:** facts are survival subjects; probe cycles are time;
probe outcomes are events; unprobed facts are *censored*, not
discarded. The Weibull exponent k tests whether retention hazard
is constant (exponential) or changes with age.

**Falsifier:** if KM curves are indistinguishable across runs
that differ in measured retention, the estimator is too coarse.

## M4. BM25 — the proven retrieval scorer
**Attacks:** raw overlap counting (common words dominate,
length bias).

    score(q,d) = SUM_t IDF(t) * f(t,d)(k1+1) /
                 (f(t,d) + k1(1 - b + b|d|/avgdl))

**Mapping:** store sentences = documents; IDF computed over the
corpus, so *rare* corpus terms are the discriminative ones.
Drop-in above the overlap counter.

**Falsifier:** if BM25 ranking fails to beat raw overlap on
banked retrieval pairs, the IDF prior is wrong for the corpus
distribution — report and keep both.

## M5. UCB1 — admission with a proof
**Attacks:** hand-tuned exploration constants in presentation
admission.

    choose arm maximizing x_bar_i + sqrt(2 ln t / n_i)
    regret bound: O(sqrt(T ln T))

**Mapping:** arms = store items; pull = presentation appearance;
reward = successful recall. Never-shown items have n_i = 0 →
infinite bonus → guaranteed exploration. The exploration
constant is derived, not declared.

**Falsifier:** if UCB admission underperforms fixed-reserve
admission on paired replays, the reward signal is too sparse —
report; the reserve was carrying more than exploration.

## M6. Edit distance / Jaccard — adjacency, quantified
**Attacks:** "plausible-wrong" answers scored by hand patterns.

    adjacency(claim) = min over real records of distance(claim, rec)

**Measured:** transposed-value grabs land at distance 1
(token-identical sets at Jaccard 0.0); semantic inventions at
~1.0. The histogram is bimodal with a gap — the threshold is
obvious, and ADJACENT becomes a number.

**Falsifier:** if adjacent vs invented distance distributions
overlap continuously, the granularity is wrong — report.

## M7. Inverted Index + Stemming — the search-engine structure
**Attacks:** linear scans and morphological misses.

    inverted index: stemmed content term -> {record ids}
    stemmer: iterative, length-guarded suffix stripping
    (consistency over linguistics: both sides of a match stem
    identically — rivers converges with river)

**Mapping:** the log is indexed once; probes look up O(1) per
stemmed term. Pure structure — no hypothesis to falsify beyond
retrieval quality in the run.

## M8. SimHash — adjacency as a fingerprint distance
**Attacks:** the same adjacency quantification at scale.

    simhash(tokens) = 64-bit weighted-vote fingerprint
    adjacency = hamming distance <= k

**Mapping:** fingerprint every record and every asserted claim;
adjacency = hamming distance. The scale-out of M6.

**Falsifier:** if known-adjacent and known-invented hamming
distributions overlap, the fingerprint width or feature weighting
is wrong.

---

## The portability thesis

Every formula above is a pure function of text and counters. None
embeds weights, training data, or model identity. They run on any
domain, any reader, any hardware. The store is instance; the math
is the machine.

---
**Michael Harding** — Afterimage. Deterministic memory for small models; measured before shipped.
