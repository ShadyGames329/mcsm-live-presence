# Contributing

Small, reproducible changes are welcome. Start an issue for a new platform, game edition or hook design so compatibility can be discussed before substantial work.

## Development checks

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
lua tests/probe_mock.lua
bash -n scripts/launch.sh
```

Keep fixtures synthetic. A mock passing does not prove a modified script executes in the game: report structural checks and runtime observations separately.

## What belongs in a contribution

- Original source, documentation and synthetic tests.
- A concrete description of expected behavior and observed results.
- Compatibility notes for any changed game assumptions.

Do not submit game archives, original or compiled game scripts, generated mod archives, saves, decryption profiles/keys, Discord tokens, personal configs or unredacted logs. Build outputs stay local and ignored.

Preserve the four-file sidecar installation model, checksum validation, original-game-file protections and launch-scoped companion lifecycle. Avoid polling more frequently or expanding API hooks without a measured need.
