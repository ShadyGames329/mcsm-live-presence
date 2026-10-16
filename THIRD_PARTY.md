# Third-party software

This repository contains original project code and synthetic fixtures. It does not vendor game resources or third-party decryption profiles.

| Dependency | Use | Source |
| :--- | :--- | :--- |
| ttg-cli-inspector | Optional local archive/sidecar builder | [Haister/ttg-cli-inspector](https://github.com/haister/ttg-cli-inspector) |
| pypresence | Discord IPC companion | [qwertyquerty/pypresence](https://github.com/qwertyquerty/pypresence) |

The optional builder is pinned to the inspected upstream commit in `pyproject.toml`. Dependencies retain their own licenses and copyright notices. No original game script or archive is shipped under this project's MIT license.
