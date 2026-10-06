---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle: consult them before and during the loop, not after.

When exploring the codebase, read `GLOSSARY.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

Judge a test by the concrete contract violation it can detect, not by execution or coverage alone. For each test, name a realistic wrong result or behavior and check that its assertions would reject it.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

When the shape of that interface is itself in question (how deep the module is, where the seam belongs, what the interface should expose), call the Skill tool with "codebase-design" for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec. Use snapshots only for a stable public contract, and review snapshot changes instead of regenerating them blindly.
- **Weak oracle**: the test checks only truthiness, existence, type, no exception, a status, or a mock call when the contract provides a meaningful value, state, or effect to assert. State which realistic wrong outcomes the assertion still allows, then assert the contract-relevant result.
- **Code-first oracle / frozen bug**: the expected result is copied from current implementation behavior without an independent contract. Check the request, specification, and documentation; a passing test must not preserve a behavior just because production currently has it.
- **Rotten green**: a critical assertion can be skipped, remain unreachable, run after an unconditional return, or fail to execute because async work was not awaited. Confirm the test framework actually observes every critical assertion.
- **Mocked-away behavior**: a mock replaces the behavior the test claims to verify, and the test checks only that the mock was called. Keep the behavior under test real and assert its caller-visible result; use the mock only to control an external boundary.
- **Flaky or redundant test**: timing, randomness, shared state, environment, or ordering can change the result; or a neighboring test already checks the same behavior. Control nondeterminism and compare behavioral coverage before adding another scenario.
- **Coverage theater / test bloat**: execution, line coverage, assertion count, or a large fixture is treated as proof of regression value. Keep only contract-relevant assertions and setup.
- **Happy-path-only suite**: many similar successes create apparent breadth while contract-relevant rejection, boundary, or failure behavior is untested. Add those scenarios when the behavior contract calls for them, not to reach a test-count target.
- **Invalid API assumption**: the test uses an unverified framework method, fixture, endpoint, signature, or configuration option. Check definitions, imports, installed dependency versions, and repository configuration before relying on it.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. The failure must come from the missing or wrong behavior, not compilation, setup, or an unrelated assertion. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Independent oracle.** Derive expected behavior from the request, a contract, or a worked example, not by calling the implementation, repeating its algorithm, or freezing unexplained current output.
- **Challenge the test.** Before keeping it, name one small realistic production mutation and confirm the test would fail. Use actual mutation tooling only when it is safe and reversible; a reasoned check is enough otherwise.
- **Verify test mechanics.** Check framework APIs against the repository's imports, dependencies, and configuration. Await async operations and assertions, and ensure the behavior under test cannot be bypassed by conditional or swallowed checks.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.
