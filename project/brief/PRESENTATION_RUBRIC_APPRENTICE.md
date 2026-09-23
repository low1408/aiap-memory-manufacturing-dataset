# Presentation Rubric (Apprentice) — "Designing a Good ML System"

**For apprentices.** This is how your **design presentation** — the primary deliverable of the week — is assessed. It tells you the format, the dimensions we grade, and what good reasoning looks like. These *are* the learning objectives, so lean into them: reasoning well about them isn't gaming, it's the point.

> Your mentors hold a companion doc with the detailed scoring scale and the live-question bank. Those stay mentor-facing on purpose — you can't pre-script answers to questions you haven't seen, and that's what keeps the viva honest.

---

## 1. What we're grading, and how

The presentation is a **viva, not a slideshow.** We grade the **quality of your design reasoning, defended live** — not the polish of your slides, and not your model's accuracy.

**Format:**

1. **Pre-read (submitted the day before).** Your notebook answers + your §10.2 design blueprint — assembled in **`PRE_READ_TEMPLATE.md`** (a fill-in doc: blueprint, architecture sketch, and the six highest-signal questions). Mentors read these to prepare questions. *They are context, not a graded artifact* — we grade what you can defend, not what you (or an LLM) wrote.
2. **Short presentation (~10 min).** Walk us through your system: the problem as you framed it, the key decisions, and what you deliberately chose *not* to do. Put an **architecture sketch on screen** (the boxes-and-arrows diagram from your notebook §10.2 blueprint) and talk over it - it's the fastest way for us to see your system whole. We read it for *what it shows about your design*, not how polished it looks; a rough diagram that reasons well beats a beautiful one that doesn't.
3. **Q&A / viva (~15 min).** We probe the reasoning. Questions go to **individuals**, not just the presenter.

**What this means for you:** we grade your *reasoning*, not your deck's looks — no marks for animations, none lost for plain slides, and a strong-reasoning / weak-delivery team isn't penalised for delivery. That is **not** a licence to present badly: a clear, well-structured walkthrough and a legible architecture sketch help us follow you and make your defence land — and communicating a design clearly is itself a real engineering skill. **The key part you're assessed on is the oral defence** (the Q&A): defending every choice under questioning — including "why not the alternative?" and "what breaks if…?".

---

## 2. Dimensions

Seven dimensions. The first six are the design; the seventh is the defense.

| # | Dimension | The question it answers |
|---|---|---|
| 1 | **Problem framing & fit** | Did they turn the vague ask into a sound problem statement (objective, task type, target, metric, baseline)? Did they ask "does this even need ML?" |
| 2 | **Cost of error & metric choice** | Does the metric reflect the *real* asymmetry of errors? Did they handle multi-class / a human-review tier / thresholds sensibly rather than defaulting to accuracy? |
| 3 | **Data & pipeline reasoning** | Can they reason about validation, leakage, and train/serve skew for their problem — even where the data is hypothetical, or (if they built) synthetic? |
| 4 | **Serving & deployment fit** | Is the serving pattern (batch / real-time / …) justified *by their constraints*? Do they understand the environment/reproducibility story? |
| 5 | **Monitoring & the loop** | Do they distinguish data vs concept drift, name proxy signals for late labels, define a retrain trigger, and see the feedback loop? |
| 6 | **Trade-offs & prioritisation** | Can they name what they *deliberately* under-invested in and defend why — a spent complexity budget, not an oversight? |
| 7 | **Live defense** | Under questioning: do they justify choices, engage with alternatives, update honestly when challenged, and own the system's weaknesses? |

**Build — an optional stretch, worth a small bonus.** Building the pipeline is an **encouraged stretch goal, not a requirement** — **never required, and never penalised if you don't get to it.** *If* you do build one and it **works as intended** — runs end-to-end, ingest → train → evaluate → predictions — it earns a **small bonus on top of your seven-dimension score: on the order of 1–2% of the overall grade.** It's judged purely on craft — **modular, config-driven, reproducible, runs end-to-end** — never on model accuracy or data realism.

**Read that number carefully: 1–2% is not worth trading design time for.** The viva is where effectively all the marks are. **A solid design with no build beats a sloppy build of a weak design** by a wide margin. Put your time into the design first; a clean pipeline is a small bonus on top of good judgement, never a substitute for it.

**Deployment — a further bonus, optional.** If a team took their system all the way to a running service (per the deployment reference notebook), it's recognised as a further small bonus on top of the build bonus. Its absence is never penalised.

**Deep-dive lenses — bonus depth.** Evidence of the six advanced lenses (trade-off, pre-mortem, feedback contamination, label bias, economics, human factors) lifts dimensions 2/3/5/6/7. Their *absence* is not penalised — the deep-dive is optional.

---

## 3. What we do and don't reward

**Reward:**
- Decisions that *fit the constraints you were given* — not maximal sophistication.
- "We chose X over Y because…" — reasoning with the alternative visible.
- Honesty about limitations and what you'd do with more time.
- Consistency: framing → metric → serving → monitoring hang together.

**Do not reward:**
- Deck aesthetics, tool name-dropping ("we'd use Kafka/Kubernetes/a feature store") without a reason the *problem* demands it.
- Jargon or buzzwords substituting for reasoning.
- Maximal complexity — reach for a feature store / real-time stack / auto-retrain loop only if the problem needs it (over-engineering is a failure too).
- A confident wrong answer left undefended when challenged.
