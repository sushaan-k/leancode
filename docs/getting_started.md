# Getting Started

`vericode` turns a natural-language or YAML specification into:

1. implementation code
2. a backend-specific proof artifact
3. a machine-check result
4. a certificate binding the spec, code, and proof bundle together

This guide covers the shortest path from install to a verified run.

## Install

```bash
pip install vericode
```

For local development:

```bash
git clone https://github.com/sushaan-k/vericode.git
cd vericode
pip install -e ".[dev]"
```

## Runtime Prerequisites

The Python package is not enough by itself. Verification only succeeds when the
selected proof assistant is installed locally.

| Backend | Local tool required | Notes |
|---|---|---|
| `lean4` | `lake` / Lean 4 toolchain | Default backend |
| `dafny` | `dafny` | Verifies generated `.dfy` source |
| `verus` | `verus` | Verifies Rust-oriented proof source |

If the backend toolchain is missing, `vericode` can still generate output, but
the verification result will reflect the missing backend rather than a proof
success.

## Configure an LLM Provider

`vericode` supports three provider families:

- `anthropic`
- `openai`
- `deepseek`

Set the matching API key in your environment:

```bash
export ANTHROPIC_API_KEY=...
# or
export OPENAI_API_KEY=...
# or
export DEEPSEEK_API_KEY=...
```

If you do not pass a provider explicitly in Python, the top-level `verify()`
path defaults to the Anthropic provider.

## Fastest CLI Path

Verify a natural-language prompt:

```bash
vericode verify "sort a list of integers" --lang python --backend lean4
```

Verify from a YAML spec file:

```bash
vericode verify --spec spec.yaml --lang rust --backend verus
```

Generate a proof for an existing implementation:

```bash
vericode prove --code sort.py --spec "output is sorted and is a permutation of input"
```

Batch a directory of YAML specs:

```bash
vericode batch --specs specs/ --output verified/
```

`batch` defaults the implementation language from the backend unless `--lang`
is supplied:

| Backend | Default batch language |
|---|---|
| `lean4` | `lean` |
| `dafny` | `dafny` |
| `verus` | `rust` |

## Python API

### Natural-language input

```python
import asyncio
from vericode import verify


async def main() -> None:
    result = await verify(
        "Write a binary search that returns the index of the target or -1.",
        language="python",
        backend="lean4",
    )
    print(result.verified)
    print(result.code)
    print(result.proof)
    print(result.certificate)


asyncio.run(main())
```

### Structured spec input

```python
import asyncio
from vericode import Spec, verify


async def main() -> None:
    spec = Spec(
        description="Merge two sorted lists into one sorted list",
        preconditions=["is_sorted(a)", "is_sorted(b)"],
        postconditions=[
            "is_sorted(result)",
            "len(result) == len(a) + len(b)",
            "is_permutation(result, a + b)",
        ],
    )
    result = await verify(spec, language="python", backend="dafny")
    print(result.verified)


asyncio.run(main())
```

## YAML Specs

The CLI accepts a YAML file through `--spec`. The parser loads that file into a
`Spec` object before generation. A practical starting point is:

```yaml
description: Binary search over a sorted list of integers
function_name: binary_search
input_types:
  arr: list[int]
  target: int
output_type: int
preconditions:
  - arr is sorted in nondecreasing order
postconditions:
  - result == -1 or 0 <= result < len(arr)
  - result == -1 or arr[result] == target
```

## Understanding the Output

`verify()` returns a `VerificationOutput` object with:

- `code`: generated or preserved implementation
- `proof`: backend-specific proof text
- `verified`: final machine-check status
- `iterations`: refinement rounds taken by the proof engine
- `backend`: backend name used for the run
- `certificate`: `ProofCertificate` binding the spec, code, and proof bundle

The certificate is designed to be machine-checkable later; it stores hashes of
the canonicalized spec, implementation, and bound proof source.

## `verify` vs `prove`

- `verify` starts from a natural-language or YAML spec and asks the model to
  generate implementation plus proof.
- `prove` starts from existing source code and asks the model to generate a
  proof for that implementation under the supplied spec.

Use `prove` when the code already exists and you want verification layered onto
it instead of regenerating the implementation from scratch.

## Recommended Local Checks

```bash
pytest
ruff check src/ tests/
mypy src/
```

## Practical Limits

- The quality of the result is bounded by the quality of the supplied spec.
- Backend installation is mandatory for an actual proof success.
- Support is strongest for the backends listed in `vericode.backends`.
- The proof guarantee is with respect to the generated or supplied spec and the
  backend-checked proof artifact, not an unstated English intent.
