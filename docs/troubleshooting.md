# Troubleshooting

## Discord does not show an activity

Keep the local Discord desktop client open. Verify that your config contains the Application ID, not an asset key or bot token. Check Discord activity privacy settings and whether another presence application is competing with this one.

Read the local `presence.log` under the state directory. Do not post complete logs publicly without removing personal paths and identifiers. The `preview` command can check formatting without Discord:

```sh
.venv/bin/python -m mcsm_live_presence preview gameplay
```

## It stays at “In session”

This means valid telemetry from the current launch has not arrived. Confirm both archives and both descriptors are installed, the game was fully restarted after installation, and Steam launches through the wrapper.

Check whether `live-state.txt` in the state directory changes. The builder embeds its Windows path in the Lua source; the config and build must use the same state directory. Verify Proton's `Z:` mapping or rebuild with `--windows-state-dir`.

```sh
.venv/bin/python -m mcsm_live_presence status
```

This inspection command accepts the most recent file regardless of age. The running companion intentionally accepts only current-launch telemetry.

## Browsing episodes still says Main Menu

Restart the game after rebuilding/installing. Check that both Project and Menu sidecar pairs belong to the same build. An older experiment can override the resource or miss the private marker; the installer refuses known LiveState experiment names for this reason.

For a diagnostic build, add `--diagnostics` to the build command, using a fresh output directory. Reinstall after removing the previous manifest-tracked version. `menu-observer.txt` should show module loading, show callbacks, and `private=true` for the episode browser. Backing out should show `private=false` for another menu.

## Chapter is missing or a location looks technical

Chapter display is conditional. The tested runtime returned no chapter value, and none is invented from saves. Scene display may use a live script ID rather than a curated location name. Set `show_scene` to `false` if you prefer episode-only presence or want to avoid location spoilers.

## Artwork is missing

The key must match an asset in the exact Discord application whose ID you configured. The application and asset keys are different values. Set `large_image_key` to an empty string to test text-only presence.

## Install or uninstall refuses to proceed

Read the error before changing anything. The tool deliberately refuses to overwrite existing files or delete files that differ from the installation manifest. Preserve the manifest and inspect the named files. Do not delete or replace the game's original archives to bypass an error.

## A different edition fails to build

Support is limited to the inspected PC Season One formats. A changed original script can fail the constructor or bytecode-layout checks. File an issue with the error and a description of the edition/platform; do not upload original or compiled scripts, game archives or saves.
