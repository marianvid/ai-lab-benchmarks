# Recommendations

## Agentic coding: prominent limitation

> [!CAUTION]
> **This tested configuration is not recommended for serious agentic software development.** The local models and hardware combinations evaluated by the owner have not been reliable enough to act as the primary autonomous executor for medium or large software projects. In repeated attempts, they did not consistently preserve requirements, architecture, repository state, and implementation intent across long cycles of planning, editing, testing, debugging, repair, and review. The practical outcome was non-convergence, incomplete implementations, repeated intervention, or the need to hand control back to a substantially more capable model.

This recommendation requires four explicit distinctions:

1. **The new controlled agentic probe is still not a project-level result.** It measures four bounded repositories, at most fourteen tool turns each, with deterministic hidden tests. A model passing those tasks has not thereby demonstrated that it can autonomously maintain a real software project over many dependent actions. See [Agentic coding probe](agentic-coding.md).

2. **The recommendation is based on repeated operational trials and the owner's experience.** The owner has repeatedly attempted to build agentic coding workflows that included local models. Those practical trials exposed failures of continuity, state tracking, architectural judgment, tool use, recovery, and sustained execution that short isolated tests do not capture. They are experience-based evidence, not a controlled agentic benchmark score.

3. **The conclusion is scoped to the tested configurations.** It does not claim that every local model or every local deployment is inherently unsuitable. It states that the tested models, quantizations, hardware, context constraints, and orchestration setup are not adequate as the primary autonomous development system for serious medium or large projects. Small, bounded, independently verifiable tasks may still be appropriate. A substantially stronger local configuration, or frontier-class models, is required for the broader role.

4. **Exhaustive agentic evaluation remains outside this benchmark's scope.** The new probe adds reproducible repositories, controlled tools and objective tests, but it is one pass over four short tasks. A rigorous project-level answer still requires longer horizons, repeated runs, failure taxonomy, intervention accounting and regression testing.

## Practical use

- Use this configuration for bounded inference and media-processing workloads demonstrated by the benchmark.
- Use local coding models only for small tasks with clear inputs, short execution horizons, deterministic checks, and inexpensive human review.
- Do not treat successful code completion, unit-test generation, or a short tool-use example as evidence of autonomous project-level reliability.
- For medium or large repositories, keep architecture, orchestration, review, and recovery under a substantially more capable model or a human-led workflow.
