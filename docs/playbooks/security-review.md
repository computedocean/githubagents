# Playbook: security review

Used by: `security-reviewer`, `dependency-supply-chain-reviewer`, `code-reviewer` (for hand-offs only).

## Map the attack surface first

List the entry points: HTTP handlers, CLI arguments, file and archive parsers, message consumers, deserializers, and CI workflow triggers. For each, note who can supply the input.

## A finding needs a path

Trace untrusted input from its **source** to a sensitive **sink**, with a `file:line` for each hop. Look for mitigations along the path (validation, encoding, parameterisation, framework protection) and try to disprove the finding before reporting it. A pattern match with no traced path is Confidence: Low.

## Severity = impact × reachability

| Reachability | Who controls the input today |
|---|---|
| `remote-unauthenticated` | anyone on the network |
| `remote-authenticated` | a signed-in user |
| `local-user` | someone who can already run the program or give it files or arguments |
| `developer-only` | build tooling, constants, tests |

Raise the severity when input crosses a trust boundary, such as a file that came from someone else. Always say how the severity would change if the code were exposed more widely.

## Common sinks to check

SQL and NoSQL query building; shell or subprocess calls; template rendering; file paths built from input (traversal, absolute paths); deserialization (`pickle`, unsafe YAML, Java serialization); outbound requests built from input (SSRF); cryptography and randomness; secrets in code, config, and CI; debug flags and permissive defaults.

## CI workflows

Watch for `pull_request_target` that checks out PR code, untrusted `${{ github.event.* }}` values interpolated into `run:` steps, `permissions: write-all`, and third-party actions not pinned to a full commit SHA.

## Safety

Describe exploits in words. Do not build working payloads, run exploits, or contact live systems. Never repeat a secret value.
