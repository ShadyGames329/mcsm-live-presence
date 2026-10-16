# Security and privacy

The companion uses a local telemetry file and local Discord IPC. It does not need a bot token, open a network listener, read saves or send analytics. Discord receives the configured activity text and artwork references through its desktop client.

Episode and location text can reveal story progress. Set `show_scene` to `false` for less detail. Configuration and runtime state are local and ignored by Git.

Do not put credentials or proprietary game files in public reports. For an ordinary bug, use the issue template with sanitized details. If a report involves sensitive data, describe the issue without attaching that data and request a private reporting channel.
