# PicoClaw Magisk Module

Packaging-only repo for PicoClaw Android arm64 Magisk/KernelSU/APatch module.

This repo does not fork or patch PicoClaw source. GitHub Actions builds upstream `sipeed/picoclaw` release tags as-is, overlays only Magisk packaging files, then publishes a release with the same tag.

## Release flow

- Stable workflow builds latest upstream non-prerelease GitHub Release.
- Nightly workflow builds upstream `nightly` ref/tag as a separate prerelease named from the upstream version, for example `v0.3.1-nightly`.
- If upstream nightly has no `v*` tag on the commit, release name falls back to `nightly-YYYYMMDD-SHA`.
- Android-patched workflow builds separate `-android` releases with only the DNS fallback patch.

- Manual trigger: Actions → Release Magisk Module → Run workflow.

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
