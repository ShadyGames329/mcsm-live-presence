# Validation and compatibility notes

## In-game observations

The development setup used a local PC Season One installation on Linux through Steam/Proton and a native Discord IPC connection. The following were observed by the user:

- Main menu, gameplay, pause, resume and return-to-menu presence.
- Live episode number/title and the current game script as a scene fallback.
- Episode-selection presence after adding the private marker to its menu instance.

The companion log independently recorded episode, current-script, gameplay/pause/menu events. A dedicated menu callback log established why an earlier browser attempt failed: actual menu objects had no `isEpisodeSelect` field despite successful callback loading and message delivery.

The chapter getter returned empty in the recorded session. Chapter availability across episodes is not established. Scene IDs are runtime identifiers, not a complete human-readable location database.

## Portable release

The portable package preserves the tested game-side hook design and removes machine-specific paths, experimental installers and save parsing. Its build output is verified locally against the inspected original scripts. This refactoring still needs a separate end-to-end smoke test before broader compatibility can be claimed. No native Windows or macOS launcher is provided.

## Automated checks

The test suite covers stale and partial telemetry, mode validation, live-only formatting, conditional chapters, private-marker insertion, unexpected bytecode rejection, overwrite refusal and checksum-guarded uninstall. Lua mocks reproduce a browser object with a private marker but no template flag, and verify that private signals do not reach the original game presence function.

Tests and CI use synthetic fixtures. No proprietary assets or encrypted game derivatives are included.

## Smoke test for a new setup

1. Build from your own game and inspect the generated manifest.
2. Close the game, install the four sidecars, and launch with Discord open.
3. Check Main Menu → Browsing Episodes → Main Menu.
4. Continue an existing save and check episode/location. Normal gameplay may autosave.
5. Pause, resume, return to menu, then quit. Check activity cleanup.
6. If anything fails, preserve local evidence and uninstall with the manifest before further tests.
