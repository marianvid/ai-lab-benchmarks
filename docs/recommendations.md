# Recommendations

## Agentic coding: prominent limitation

> [!CAUTION]
> **This tested configuration is not recommended for serious agentic software development.** The local models and hardware combinations evaluated by the owner have not been reliable enough to act as the primary autonomous executor for medium or large software projects. In repeated attempts, they did not consistently preserve requirements, architecture, repository state, and implementation intent across long cycles of planning, editing, testing, debugging, repair, and review. The practical outcome was non-convergence, incomplete implementations, repeated intervention, or the need to hand control back to a substantially more capable model.

This recommendation requires four explicit distinctions:

1. **Controlled benchmark results are not agentic-coding results.** The published benchmark measures bounded capabilities such as inference speed, resource use, image generation, OCR, audio processing, and narrowly scoped coding tasks. A model passing those tests has not thereby demonstrated that it can autonomously maintain a real software project over many dependent actions.

2. **The recommendation is based on repeated operational trials and the owner's experience.** The owner has repeatedly attempted to build agentic coding workflows that included local models. Those practical trials exposed failures of continuity, state tracking, architectural judgment, tool use, recovery, and sustained execution that short isolated tests do not capture. They are experience-based evidence, not a controlled agentic benchmark score.

3. **The conclusion is scoped to the tested configurations.** It does not claim that every local model or every local deployment is inherently unsuitable. It states that the tested models, quantizations, hardware, context constraints, and orchestration setup are not adequate as the primary autonomous development system for serious medium or large projects. Small, bounded, independently verifiable tasks may still be appropriate. A substantially stronger local configuration, or frontier-class models, is required for the broader role.

4. **Exhaustive agentic evaluation is outside this benchmark's current scope.** A rigorous answer would require reproducible repositories, long-horizon tasks, controlled tool access, repeated runs, failure taxonomy, intervention accounting, regression testing, and objective completion criteria. Agentic coding benchmarks may be added later to identify the practical limits more precisely, but this is not currently a priority for the author.

## Practical use

- Use this configuration for bounded inference and media-processing workloads demonstrated by the benchmark.
- Use local coding models only for small tasks with clear inputs, short execution horizons, deterministic checks, and inexpensive human review.
- Do not treat successful code completion, unit-test generation, or a short tool-use example as evidence of autonomous project-level reliability.
- For medium or large repositories, keep architecture, orchestration, review, and recovery under a substantially more capable model or a human-led workflow.
