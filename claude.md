# vericode

## Formally Verified AI Code Generation

### The Problem

AI code generation is everywhere — Claude Code, Cursor, Copilot — but none of it comes with guarantees. The industry coined "vibe coding" to describe the workflow: generate code, hope it works, manually test, ship. Martin Kleppmann's widely-cited December 2025 piece argued that **formal verification will go mainstream via AI** — but nobody has shipped the tool that makes this real.

The pieces exist separately:
- LLMs can generate code (but with bugs)
- Proof assistants (Lean 4, Dafny, Verus) can verify code (but require expert knowledge)
- DeepSeek-Prover-V2 showed LLMs can generate proofs (but it's a research model, not a tool)

Nobody has connected these into a usable pipeline: **natural language → code + proof → verified binary**.

### The Solution

`vericode` is a CLI tool and library that takes a natural language specification, generates both implementation code and a formal proof of correctness, and verifies the proof compiles — all in one command.

### Pipeline

```
Natural Language Spec
        │
        ▼
┌─────────────────┐
│  Spec Parser     │  Extracts: types, preconditions, postconditions,
│                  │  invariants from natural language
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dual Generator  │  Simultaneously generates:
│                  │  1. Implementation (Python/Rust/TS)
│                  │  2. Formal spec (Lean 4 / Dafny)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Proof Engine    │  Attempts to prove the implementation
│                  │  satisfies the formal spec. If proof
│                  │  fails, feeds error back to generator
│                  │  for iterative refinement.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Verifier        │  Runs the proof assistant compiler
│                  │  (lean4 / dafny verify) to confirm
│                  │  the proof is machine-checked.
└────────┬────────┘
         │
         ▼
   Verified Code + Proof Certificate
```

### Core Components

#### 1. Spec Parser
Converts natural language into structured specifications:

```python
# Input (natural language)
"""
Write a function that sorts a list of integers.
The output must be a permutation of the input.
The output must be in non-decreasing order.
The function must handle empty lists.
"""

# Output (structured spec)
Spec(
    function_name="sort",
    input_types={"lst": "List[int]"},
    output_type="List[int]",
    preconditions=[],
    postconditions=[
        "is_permutation(output, input.lst)",
        "is_sorted(output)",
    ],
    edge_cases=["lst == []"],
)
```

#### 2. Dual Generator
Uses an LLM to generate **both** the implementation and the formal proof simultaneously. This is key — generating them together ensures they're aligned.

```
┌─────────────────────────────────────────┐
│ LLM generates in a single pass:         │
│                                         │
│ // Implementation (Python)              │
│ def sort(lst: list[int]) -> list[int]:  │
│     ...                                 │
│                                         │
│ // Proof (Lean 4)                       │
│ theorem sort_correct :                  │
│   ∀ (lst : List Int),                   │
│   is_permutation (sort lst) lst ∧       │
│   is_sorted (sort lst) := by            │
│     ...                                 │
└─────────────────────────────────────────┘
```

#### 3. Proof Engine (Iterative Refinement)
The proof rarely compiles on the first try. The engine runs an iterative loop:

1. Generate code + proof
2. Run proof assistant
3. If error → extract error message
4. Feed error + context back to LLM
5. LLM fixes the proof (or the code)
6. Repeat (max N iterations)

This is where the magic happens. The LLM + proof assistant form a feedback loop that converges on correct code.

#### 4. Verifier
Final machine-checked verification. If the proof compiles in Lean 4 or Dafny, the code is **mathematically proven correct** against the spec. This is not testing — this is proof.

### Supported Verification Backends

| Backend | Target Language | Maturity | Best For |
|---------|----------------|----------|----------|
| Lean 4  | Lean           | Production | Mathematical proofs, algorithmic correctness |
| Dafny   | C#, Java, Python, Go, JS | Production | Systems code, data structures |
| Verus   | Rust           | Beta | Performance-critical systems code |

### Technical Stack

- **Language**: Python 3.11+ (CLI and orchestration)
- **LLM**: Any model via API (Claude, GPT, DeepSeek-Prover)
- **Proof assistants**: Lean 4, Dafny (installed as subprocesses)
- **CLI**: `click` or `typer`
- **Output**: Verified source files + proof certificates

### API Surface (Draft)

```python
from vericode import verify, Spec

# Simple: one-liner
result = verify(
    "Write a binary search that returns the index of a target in a sorted array, or -1 if not found.",
    language="python",
    backend="lean4",
)
print(result.code)            # The implementation
print(result.proof)           # The Lean 4 proof
print(result.verified)        # True if proof compiles
print(result.iterations)      # How many refinement rounds
print(result.certificate)     # Machine-verifiable proof certificate

# Advanced: explicit spec
spec = Spec(
    description="Merge two sorted lists into one sorted list",
    preconditions=["is_sorted(a)", "is_sorted(b)"],
    postconditions=[
        "is_sorted(result)",
        "len(result) == len(a) + len(b)",
        "is_permutation(result, a + b)"
    ]
)

result = verify(spec, language="python", backend="dafny", max_iterations=10)
```

### CLI

```bash
# Verify a natural language spec
$ vericode verify "sort a list of integers" --lang python --backend lean4

# Verify from a spec file
$ vericode verify --spec spec.yaml --lang rust --backend verus

# Generate proof for existing code
$ vericode prove --code sort.py --spec "output is sorted permutation of input"

# Batch verification
$ vericode batch --specs specs/ --output verified/
```

### What Makes This Novel

1. **First usable "natural language → verified code" pipeline** — connects the dots nobody else has
2. **Iterative LLM + proof assistant feedback loop** — the key insight that makes it work
3. **Multi-backend** — Lean 4, Dafny, Verus support
4. **Practical, not academic** — a CLI tool developers actually use, not a research paper
5. **Proof certificates** — machine-verifiable artifacts you can ship with your code

### Difficulty & Scope

This is genuinely hard. Some notes on scoping:
- **V1**: Support simple algorithms (sorting, searching, data structures). These have well-understood proof strategies.
- **V2**: Support more complex specs (concurrent code, I/O, stateful systems).
- **V3**: Custom proof tactics library that the LLM can draw from.

Start narrow, ship early, expand based on what proofs the LLM can actually generate reliably.

### Repo Structure

```
vericode/
├── README.md
├── pyproject.toml
├── src/
│   └── vericode/
│       ├── __init__.py
│       ├── spec.py             # Spec parsing and representation
│       ├── generator.py        # Dual code + proof generation
│       ├── proof_engine.py     # Iterative refinement loop
│       ├── verifier.py         # Proof assistant interface
│       ├── backends/
│       │   ├── lean4.py        # Lean 4 backend
│       │   ├── dafny.py        # Dafny backend
│       │   └── verus.py        # Verus backend
│       ├── models/
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── deepseek.py     # DeepSeek-Prover integration
│       └── cli.py
├── proofs/                     # Library of proof tactics
│   ├── sorting.lean
│   ├── searching.lean
│   └── data_structures.lean
├── tests/
│   ├── test_sorting.py
│   ├── test_searching.py
│   └── test_data_structures.py
├── examples/
│   ├── binary_search.py
│   ├── merge_sort.py
│   └── balanced_bst.py
└── docs/
    ├── getting_started.md
    ├── supported_specs.md
    └── adding_backends.md
```

### Research References

- Martin Kleppmann, "AI will make formal verification go mainstream" (Dec 2025)
- DeepSeek-Prover-V2 (arXiv:2509.22908)
- Lean 4 documentation (lean-lang.org)
- Dafny documentation (dafny.org)
- "Towards Neural Program Synthesis with Verification" (ICLR 2025)
- "LLM-Generated Code Verification: A Survey" (ACM Computing Surveys, 2025)
