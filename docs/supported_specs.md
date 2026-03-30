# Supported Specs

`vericode` accepts either:

- a natural-language description string
- a structured `Spec` object
- a YAML file that can be loaded into `Spec`

This document describes what the current parser and verification pipeline expect
and what maps cleanly to the available backends.

## The `Spec` Model

The public `Spec` type is the contract carried through parsing, generation, and
certificate binding.

Common fields used by the package and tests:

- `description`
- `function_name`
- `input_types`
- `output_type`
- `preconditions`
- `postconditions`
- `invariants`
- `edge_cases`

Only `description` is required at construction time; the parser and generator
attempt to infer the rest when absent.

## Good Spec Shapes

The best results come from specs that are:

- single-function oriented
- explicit about inputs and outputs
- explicit about preconditions and postconditions
- deterministic
- algorithmically checkable

Example:

```yaml
description: Merge two sorted integer lists
function_name: merge_sorted
input_types:
  a: list[int]
  b: list[int]
output_type: list[int]
preconditions:
  - a is sorted
  - b is sorted
postconditions:
  - result is sorted
  - len(result) == len(a) + len(b)
  - result is a permutation of a + b
edge_cases:
  - one input is empty
  - both inputs are empty
```

## Natural-Language Specs

Natural-language input works best when it names:

- the function behavior
- the expected return value
- failure behavior or sentinels
- ordering, uniqueness, or conservation properties
- edge-case handling

Good:

```text
Write a binary search that returns the index of a target in a sorted array,
or -1 if the target is not present.
```

Weaker:

```text
make binary search
```

The latter is parseable, but it gives the generator much less structure to work
with.

## YAML Specs

The CLI loads YAML specs with `vericode verify --spec spec.yaml`.

In practice, a YAML spec should map directly onto `Spec` fields. The safest
shape is:

```yaml
description: ...
function_name: ...
input_types: {}
output_type: ...
preconditions: []
postconditions: []
invariants: []
edge_cases: []
```

You do not need every field, but explicit fields reduce ambiguity.

## Supported Problem Classes

The current pipeline is strongest on:

- sorting and searching
- array and list transformations
- data-structure invariants
- pure or mostly pure helper functions
- textbook algorithms with crisp contracts

The included proofs and tests are centered on those categories.

## Language and Backend Matrix

The implementation language and the proof backend are related but not
identical.

| Backend | Backend id | Default implementation language in `batch` | Typical use |
|---|---|---|---|
| Lean 4 | `lean4` | `lean` | theorem-oriented proofs |
| Dafny | `dafny` | `dafny` | contract-heavy verified programs |
| Verus | `verus` | `rust` | Rust-oriented verification workflows |

Outside batch mode you can still pass `--lang` or `language=...` explicitly.

## Existing-Code Specs

`vericode prove --code ... --spec ...` uses:

- existing implementation code from disk
- a natural-language spec string parsed into `Spec`
- a selected backend and provider

This is the right path when the implementation already exists and only the
proof artifact needs generation/refinement.

## What the Parser Does Not Magically Infer

Do not rely on the parser to recover:

- full type signatures from vague prose
- domain-specific invariants that were never stated
- performance guarantees
- concurrency semantics
- side-effect constraints unless you state them

If those properties matter, put them in `preconditions`, `postconditions`,
`invariants`, or `edge_cases`.

## Practical Authoring Guidance

- Prefer one function per spec.
- Use named outputs and exact sentinels such as `-1`, `None`, or raised errors.
- State sortedness, permutation, bounds, and monotonicity explicitly.
- Put unusual inputs under `edge_cases`.
- Keep the first version simple; split large contracts into smaller verified
  functions when possible.

## Supported Providers

Provider choice does not change the spec format. The current provider registry
supports:

- `anthropic`
- `openai`
- `deepseek`

Provider selection affects generation quality and latency, not the `Spec`
schema.

## Limits

- The guarantee is only as strong as the stated spec.
- Backends verify backend-specific proof source, so expressivity and ergonomics
  vary by backend.
- Ambiguous English specs may still parse, but they are a poor production
  contract.
