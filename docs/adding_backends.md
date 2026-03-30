# Adding Backends

`vericode` treats each proof assistant as an implementation of a shared
`VerificationBackend` protocol. Adding a backend means implementing that
protocol, registering it, and covering it with tests.

## The Required Interface

Every backend subclasses `VerificationBackend` and implements:

- `name`
- `check_installed()`
- `verify(proof_source)`
- `format_proof_template(function_name, implementation, spec_conditions)`

The abstract base lives in `src/vericode/backends/base.py`.

## Backend Responsibilities

### `name`

Return the canonical backend identifier used by the registry and CLI, such as:

- `lean4`
- `dafny`
- `verus`

### `check_installed()`

Perform the lightest reasonable runtime check that the toolchain exists on the
current machine.

Examples:

- probe for an executable on `PATH`
- run a `--version` style command
- validate a local wrapper binary exists

This method should return `False` instead of raising on a normal “not
installed” condition.

### `verify(proof_source)`

This is the machine-check boundary. The method should:

1. materialize proof source in the backend’s expected format
2. invoke the backend toolchain
3. capture stdout/stderr
4. translate backend output into `VerificationResult`

`VerificationResult` carries:

- `success`
- `compiler_output`
- `errors`
- `elapsed_seconds`
- `backend`
- `timestamp`

Backend implementations should return structured errors when possible, not just
raw compiler output.

### `format_proof_template(...)`

This method builds the scaffold sent to the LLM before proof generation. It
should:

- include the implementation in the backend’s preferred embedding form
- encode preconditions and postconditions into a backend-native proof skeleton
- stay minimal enough that the proof engine can iterate on it

The template does not need to be a complete proof. It needs to be a good
starting point for the model and refinement loop.

## Registry Integration

After the backend class exists, register it in
`src/vericode/backends/__init__.py` by:

1. importing the class
2. adding it to `__all__`
3. adding it to `_REGISTRY`

The registry powers:

- `get_backend(...)`
- CLI `--backend` validation
- programmatic backend resolution from strings

If you skip the registry step, the backend exists in code but is unreachable
through the normal API.

## CLI Integration

The current CLI uses explicit `click.Choice(...)` lists for backend flags. When
adding a new backend, update the backend choices in `src/vericode/cli.py` for:

- `vericode verify --backend`
- `vericode prove --backend`
- any batch behavior that depends on default implementation language

If the backend implies a native language for batch output, update
`_BATCH_LANGUAGE_BY_BACKEND`.

## Testing Expectations

A new backend should ship with tests for:

- registry lookup
- installed/not-installed detection
- successful verification
- failed verification and error parsing
- proof template formatting
- CLI/backend selection paths when applicable

Prefer mocking the external toolchain in unit tests. Keep true end-to-end tests
optional and isolated from default CI unless the toolchain is reliably
available.

## Minimal Skeleton

```python
from vericode.backends.base import VerificationBackend, VerificationResult


class MyBackend(VerificationBackend):
    @property
    def name(self) -> str:
        return "mybackend"

    async def check_installed(self) -> bool:
        ...

    async def verify(self, proof_source: str) -> VerificationResult:
        ...

    def format_proof_template(
        self,
        function_name: str,
        implementation: str,
        spec_conditions: list[str],
    ) -> str:
        ...
```

## Design Guidance

- Keep backend-specific parsing inside the backend module.
- Return consistent error lists even when the backend emits noisy output.
- Bound subprocess execution with the backend timeout.
- Prefer deterministic temporary file handling.
- Do not silently coerce one backend into another; unsupported backends should
  fail at resolution time.

## Related Extension Point: Providers

If the new backend is being added alongside a new model provider, provider
registration is separate and lives under `src/vericode/models/__init__.py`.
Backends are proof systems; providers are LLM transport adapters.
