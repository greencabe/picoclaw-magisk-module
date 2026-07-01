# PicoClaw Magisk Module

Packaging-only repo for PicoClaw Android arm64 Magisk/KernelSU/APatch module.

This repo does not fork or patch PicoClaw source. GitHub Actions builds upstream `sipeed/picoclaw` release tags as-is, overlays only Magisk packaging files, then publishes a release with the same tag.

## Release flow

- Manual trigger: Actions → Release Magisk Module → Run workflow.
- Scheduled trigger checks latest upstream `v*` tag.
- If this repo has no release for that tag, it builds `picoclaw-magisk.zip`.
- Use `force=true` to replace an existing release asset.

## Runtime

- Binary: `/data/adb/modules/picoclaw/bin/picoclaw`
- Launcher: `/data/adb/modules/picoclaw/bin/picoclaw-launcher`
- Config/state: `/data/adb/picoclaw`
- Logs: `/data/adb/picoclaw/logs`
- Dashboard: `http://127.0.0.1:18800`
- Root manager WebUI redirects to dashboard.
- Root manager Action prints color-coded service health.
- Termux wrappers install as `~/bin/picoclaw` and `~/bin/picoclawctl`.

## Control

```sh
picoclawctl status
picoclawctl onboard
picoclawctl restart
picoclawctl logs 200
```
