# CLAUDE.md — Project Memory & Analysis Brief

> **Purpose of this file.** This document is written *for Claude* (the AI assistant), not for human developers. When the user starts a new conversation about this project, they will paste or attach this file instead of re-uploading all source files and re-explaining past bugs. Read this file first to reconstruct the full mental model of the project: architecture, function map, control flow, invariants, and the history of bugs already fixed. Treat the "Known Issues & Lessons Learned" and "Invariants" sections as hard constraints — do **not** re-introduce bugs that were already solved, and do **not** break the documented invariants.

---

## 1. What this project is

A single-file **PyQt5 desktop GUI** that manages a **SOCKS proxy SSH tunnel** built on top of `autossh`. It is cross-platform-aware (Linux primary, Windows/macOS partially supported) but the primary target is **Ubuntu/GNOME Linux**.

- **Display name:** `SSH Tunnel Proxy` (was previously `SSH Tunnel Manager`, and before that `autossh-manager`).
- **Slug / config dir name:** `ssh-tunnel-proxy` → config stored at `~/.config/ssh-tunnel-proxy/`.
- **Version:** `1.2.2`.
- **Language of UI:** bilingual, Persian (`fa`, default) + English (`en`), fully translated via the `TR` dict. RTL is applied automatically for Persian.
- **Files:**
  - `main.py` — the entire application (~2600 lines, single module).
  - `pyproject.toml` — packaging metadata + pinned deps (PyInstaller build target).

### Core behavior in one paragraph
The user defines one or more "server" profiles (IP, SSH port, user, key/password, tunnel port `-D`, monitor port `-M`). Pressing the big power button runs `autossh ... -D <port> -N user@ip`, then the app **actively verifies** the tunnel by doing a real SOCKS5 handshake against the local dynamic port. Once verified, it optionally sets the **system SOCKS proxy** (GNOME gsettings / Windows registry) and optionally writes **terminal proxy env vars** to a sourced file. On disconnect/failure it reverts everything (system proxy → Automatic, terminal env → cleared). A periodic health check detects drops and shows a "reconnecting" state while autossh self-heals.

---

## 2. Runtime requirements & environment notes

- **Python:** pinned to `==3.13.*` in `pyproject.toml`.
- **External binaries (runtime, not pip):**
  - `autossh` — **required** to run a tunnel. The app checks `shutil.which("autossh")` and warns + shows install command if missing.
  - `sshpass` — **only** required when a profile uses password auth (no key). Checked lazily.
  - `gsettings` — required for automatic **system** proxy control on Linux; only present under GNOME-family desktops. If absent, automatic system-proxy is unsupported and the app falls back to telling the user to set SOCKS manually.
- **Platform support reality:**
  - **Linux/GNOME:** full support (system proxy via gsettings, autostart via `.desktop`, terminal proxy via shell rc files, SIGUSR1 ssh restart).
  - **Windows:** partial — system proxy via WinINET registry; autostart via `HKCU\...\Run`; no SIGUSR1 (autossh self-restarts); terminal/rc-file proxy is a no-op ("Not applicable on Windows.").
  - **macOS:** detected as a distinct OS but largely falls into the non-Windows/non-gsettings path; system-proxy automation is effectively unsupported unless gsettings exists (it won't). Treat macOS as "best effort."

---

## 3. High-level architecture

Everything lives in `main.py`. Logical layers, top to bottom:

1. **Constants & i18n** — `APP_NAME`, `APP_SLUG`, `APP_VERSION`, config-dir migration, `TR` (translations), `THEMES` (light/dark color palettes), `qss()` (stylesheet generator).
2. **Custom widgets / icons** — `_draw_power`, `make_power_icon`, `PowerButton`.
3. **Tunnel health probes** — `socks_port_listening`, `socks5_handshake_ok`.
4. **`TunnelController(QObject)`** — owns the `autossh` subprocess (a `QProcess`), the verify/health state machine, and emits Qt signals.
5. **OS detection & install helpers** — `detect_os`, `linux_distro_ids`, `install_primary_command`, `install_note`.
6. **System proxy control** — gsettings/WinINET wrappers: `set_system_socks`, `set_system_proxy_auto`, `_gsettings_set/get`, `_win_set_proxy`.
7. **Terminal proxy (env vars + shell rc hooks)** — `write_terminal_proxy`, `clear_terminal_proxy`, `install_rc_hook`, `remove_rc_hook`, `_strip_managed_block`, `rc_hook_installed`, `_rc_targets`.
8. **Autostart on boot** — `autostart_enabled`, `set_autostart`, `_app_launch_command`.
9. **Process cleanup** — `_pid_is_autossh`, `kill_pid_tree`, `force_kill_pid`.
10. **UI widgets** — `LogDrawer`, `ServerRow`, `ServerDialog`.
11. **`MainWindow(QWidget)`** — the whole UI, config persistence, tray icon, event wiring, and orchestration of layers 4/6/7/8/9.
12. **`main()`** — QApplication bootstrap.

> **Single source of truth for naming:** `APP_NAME` / `APP_SLUG`. The window title, tray tooltip, autostart entry name, and shell-rc comment markers all derive from these (directly or via the migration lists). If renaming again, update both constants **and** add the previous slug to the migration lists (see Invariants).

---

## 4. Configuration & persistence

- **Config file:** `~/.config/ssh-tunnel-proxy/config.json` (JSON, UTF-8, `ensure_ascii=False`).
- **Keys stored in `self.cfg`:**
  - `profiles` — list of server dicts (see schema below).
  - `active` — id of the currently selected profile.
  - `theme` — `"light"` | `"dark"`.
  - `scale` — UI font scale percent (80–160).
  - `lang` — `"fa"` | `"en"`.
  - `autostart` — bool (run at boot).
  - `autoconnect` — bool (auto-connect last server at launch; only meaningful if `autostart` is on).
  - `term_proxy` — bool (route terminal through tunnel via env vars).
  - `tracked_pids` — list of PIDs of autossh processes this app created (for orphan cleanup).
  - `win_w`, `win_h` — persisted window size.
  - `warned_install` — bool (one-time autossh-missing warning shown).
  - `tray_hint_shown` — bool (one-time tray hint shown).
  - `_migrated_mon0` — bool (one-time migration flag; see below).

- **Server profile schema** (produced by `ServerDialog.data()`):
  ```
  {
    "id": <8 hex chars, os.urandom(4).hex()>,
    "name": str,
    "ip": str,
    "user": str (default "root"),
    "ssh_port": str (default "22"),
    "dyn_port": str (default "1085"),   # the -D SOCKS port
    "mon_port": str (default "0"),      # the -M monitor port; 0 = OFF (intentional default)
    "key": str (path to SSH key),
    "password": str (used only if no key, via sshpass),
    "extra": str (extra ssh options, space-split),
    "set_socks": bool (auto-set system SOCKS on connect)
  }
  ```

- **Config migrations (run on load):**
  - **Directory migration** (module top): if the new config dir does not exist, rename the first existing old dir into it. Old dirs list = `["ssh-tunnel-manager", "autossh-manager"]`.
  - **`_migrate_config`**: one-time, forces every profile's `mon_port` to `"0"` (flag `_migrated_mon0`). This exists because old `-M` values caused a serious bug (see Known Issues #1).

---

## 5. The tunnel state machine (most important to understand)

`TunnelController` is the heart. States (string, emitted via `state_changed` signal): `"off"`, `"connecting"`, `"on"`, `"reconnecting"`, `"error"`.

### Signals
- `log(str)` → appended to the log drawer.
- `state_changed(str)` → drives `MainWindow.on_state()` (UI + proxy side effects).
- `pid_started(int)` / `pid_stopped(int)` → PID tracking in config.
- `failed(str)` → a TR key describing a real connection failure; shown in a message box.

### Verify flow (`start` → `_on_started` → `_verify_step`)
1. `start(prof)` kills any existing process, builds the command, frees the local dynamic port (`_ensure_local_port_free`), launches the `QProcess`, sets state `connecting`.
2. `_on_started` records the PID and kicks off `_verify_step` after 1.5s.
3. `_verify_step` (retried every 1.5s, up to 13 tries ≈ 20s):
   - If monitor-port forwarding already failed → `_fail("verify_fwd_fail")`.
   - If process died → `_fail("verify_fail")`.
   - If `socks_port_listening` AND `socks5_handshake_ok` returns `"ok"` or `"handshake"` → mark verified, state `on`, start health timer.
   - Else retry; after max tries → `_fail("verify_fail")`.

### Health flow (`_health_check`, every 8s once verified)
- Probes listening + SOCKS5 handshake.
- If alive again after a dip → back to `on` (and log "healthy again").
- 2 consecutive fails → state `reconnecting` (proxy is NOT reverted; we expect autossh to heal).
- ≥15 fails (~2 min) → `_restart_ssh_child()` via SIGUSR1, then reset counter to 3.

### Failure / stop
- `_fail(msg_key)` emits `failed`, tears down the process cleanly, state `error`.
- `stop()` is the clean manual stop; terminates process, frees local port, state `off`.
- `_on_finished`: if we were `connecting` and never verified → emit `failed` + `error`; otherwise `off`. Guarded by `_stopping` / `error` so intentional teardown doesn't flip state.

### Key SOCKS5 probe semantics (`socks5_handshake_ok`)
Returns one of three values — **do not collapse these**:
- `"ok"` — full SOCKS5 CONNECT to a test target (1.1.1.1 / 8.8.8.8 :80) succeeded → tunnel definitely works end-to-end.
- `"handshake"` — SOCKS5 negotiation succeeded but CONNECT to test targets failed → proxy is alive locally; treated as acceptable (some servers block the test targets).
- `""` — nothing usable → failure.
Both `"ok"` and `"handshake"` count as "tunnel up."

### autossh command construction (`build_command`)
```
autossh -M <mon> -D <dyn> -N
  -o ServerAliveInterval=10 -o ServerAliveCountMax=3
  -o ExitOnForwardFailure=yes
  -o StrictHostKeyChecking=accept-new
  -o TCPKeepAlive=yes
  -o ConnectTimeout=10 -o ConnectionAttempts=3
  -p <ssh_port>
  [-i <key>] [<extra opts split on spaces>]
  user@ip
```
- If password + no key → prefixed with `sshpass -p <password>`.
- Env: `AUTOSSH_DEBUG=1`, `AUTOSSH_GATETIME=0`.
- Disconnect detection relies on `ServerAlive*`, **not** on `-M` monitoring (monitor defaults to 0). This is deliberate — see Known Issues #1.

---

## 6. Proxy control flow (system + terminal)

### System SOCKS (`set_system_socks(port)`)
- **Linux/GNOME:** sets `org.gnome.system.proxy.socks` host=127.0.0.1, port=<port>; **clears** `org.gnome.system.proxy.http/https/ftp` (host="", port=0); then sets mode=`manual`; verifies mode actually committed.
- **Windows:** WinINET registry, `ProxyServer = "socks=127.0.0.1:<port>"`, `ProxyEnable=1`, then notifies WinINET.
- Clearing HTTP/HTTPS/FTP on connect is **intentional** (added per user request) so only SOCKS is active in manual mode and stale user proxies don't interfere.

### Revert to Automatic (`set_system_proxy_auto()`)
- **Linux/GNOME:** sets mode=`auto` (verified), then clears socks host/port AND http/https/ftp host/port. Mode change is the critical step; clearing manual values is best-effort.
- **Windows:** `ProxyEnable=0` (direct/automatic).

> **gsettings gotcha (already handled):** `gsettings set` can return exit code 0 even when the commit to dconf silently failed (e.g. no D-Bus session). Therefore `_gsettings_set` checks stderr for "failed to commit", and the setters **read back** the mode with `_gsettings_get` to confirm. Don't remove these read-back verifications.

### Terminal proxy (env vars)
- `write_terminal_proxy(port)` writes `~/.config/ssh-tunnel-proxy/proxy.env` exporting `http(s)_proxy`, `ftp_proxy`, `all_proxy` (+ uppercase) = `socks5h://127.0.0.1:<port>`, plus `no_proxy` for localhost.
- `clear_terminal_proxy()` rewrites the same file to `unset` everything.
- The file is **sourced** from shell rc files via a managed block delimited by markers:
  - `RC_MARK_BEGIN = "# >>> SSH Tunnel Proxy proxy >>>"` / `RC_MARK_END = "# <<< SSH Tunnel Proxy proxy <<<"`.
  - `install_rc_hook()` adds the block (idempotent — strips any prior managed block first).
  - `remove_rc_hook()` removes it.
  - `_strip_managed_block()` recognizes **both** current and legacy markers (`_RC_MARK_BEGINS` / `_RC_MARK_ENDS`) so renamed-version blocks are cleaned, not duplicated.
- Targets: `.bashrc`, `.zshrc`, `.profile` (whichever exist; defaults to creating `.bashrc`).
- **Important UX caveat baked into the hint text:** env vars only affect terminals opened *after* the change; existing terminals need `source ~/.bashrc`. There is no transparent system-wide (TUN) routing.

---

## 7. Process / orphan cleanup

- `_pid_is_autossh(pid)` verifies a PID is actually an autossh process before killing — protects against PID reuse. Linux reads `/proc/<pid>/comm`; Windows uses `tasklist`; macOS uses `ps -o comm=`.
- `kill_pid_tree(pid)` kills the autossh PID and its children (the ssh child). Guarded by `_pid_is_autossh`.
- `force_kill_pid(pid)` SIGKILL fallback (Linux/mac only).
- `_cleanup_orphan_tunnels()` (MainWindow) closes leftover tracked PIDs from previous runs before opening a new tunnel, so processes don't pile up and leak memory.
- `do_pkill()` (Settings + tray) closes ALL app-created tunnels, reverts system + terminal proxy, clears `tracked_pids`.

---

## 8. MainWindow orchestration map

UI is three tabs in a `QStackedWidget` + a slide-out log drawer + a frameless custom title bar + a system tray icon.

- **Tabs:** Home (`_page_home`), Servers (`_page_servers`, scroll-wrapped), Settings (`_page_settings`, scroll-wrapped).
- **Home:** server picker pill, big `PowerButton`, status label, info rows (server/tunnel/socks), manual "set SOCKS" / "automatic" buttons.
- **Servers:** list of `ServerRow` widgets (edit/delete), "new server" → `ServerDialog`.
- **Settings:** autossh status + install command, language/scale/theme, startup (autostart + autoconnect), terminal proxy toggle + hint + copy button, "close app tunnels" (pkill), version label.
- **Tray:** connect/disconnect, server submenu (exclusive check group), show window, pkill, quit. Icon color reflects state.

### Signal wiring (set in `__init__`)
- `tunnel.log` → `on_log`
- `tunnel.state_changed` → `on_state`  (this is where proxy side-effects fire)
- `tunnel.pid_started` → `_track_pid`
- `tunnel.pid_stopped` → `_untrack_pid`
- `tunnel.failed` → `_on_tunnel_failed`

### `on_state(state)` side effects (critical)
- `on`: set power green, status text; if profile `set_socks` → `set_system_socks`; if `term_proxy` → `write_terminal_proxy`; sets `_proxy_applied = True`.
- `connecting` / `reconnecting`: busy color, no proxy change.
- `error` / `off`: if `_proxy_applied` → `_revert_all_proxy()` (system→auto + clear terminal env), reset flag. The `_proxy_applied` guard prevents reverting proxy the app never set.

### Window/UX details
- Frameless window: dragging via header mouse events; double-click toggles maximize; `QSizeGrip` for resize.
- Window size persisted with a 500ms debounce timer (`_persist_window_size`); excludes the open log drawer width.
- Default height fits the Home tab content once (`_fit_height_to_home`) if no saved height.
- Closing the window hides to tray (doesn't quit) unless `_really_quit` (set by `quit_app`).
- `retranslate()` re-applies all translated strings and layout direction; called on language change.

---

## 9. Invariants — DO NOT BREAK THESE

1. **Renaming the app** requires editing `APP_NAME` and `APP_SLUG` **and** appending the previous slug to `_OLD_CONFIG_DIRS`, the previous `.desktop` name to `_OLD_AUTOSTART_FILES`, and the previous rc markers to `_RC_MARK_BEGINS` / `_RC_MARK_ENDS`. Otherwise users lose their saved servers/settings, get duplicate autostart entries, or leave stale blocks in `.bashrc`.
2. **Monitor port `-M` defaults to `0` (off).** Do not change the default back to a nonzero value. See Known Issues #1.
3. **`socks5_handshake_ok` returns a 3-way value** (`"ok"`/`"handshake"`/`""`). Callers must treat both `"ok"` and `"handshake"` as success.
4. **gsettings setters must read back and verify** (mode commit can silently fail). Keep the verification.
5. **Never kill a PID without `_pid_is_autossh` first** (PID-reuse safety).
6. **`_proxy_applied` flag** gates proxy revert. Keep it accurate: set True whenever the app applies system/terminal proxy, revert only when True.
7. **`on_state` is the single place** that applies/reverts proxy as a side effect of tunnel state. Don't scatter proxy mutations elsewhere (except the explicit manual buttons and `do_pkill`).
8. **HTTP/HTTPS/FTP system proxy fields are cleared on connect and on revert** (intentional, user-requested). Keep both sides symmetric.

---

## 10. Known Issues & Lessons Learned (history of bugs already fixed)

> These are real problems that came up earlier. They are **already solved** in the current code. Re-read before changing related areas so you don't regress.

### #1 — `-M` monitor port caused fake "connected" + restart loop  *(FIXED)*
**Symptom:** the tunnel would appear up but traffic didn't flow, and autossh entered a restart loop emitting `remote port forwarding failed`.
**Cause:** autossh's `-M` monitor uses a remote port-forward. After a disconnect the monitor port wasn't freed immediately on the server, so the next attempt failed with "remote port forwarding failed", looping forever.
**Fix:**
- Default `mon_port` to `"0"` (monitor disabled) for new profiles, and one-time migrate existing profiles to `0` (`_migrate_config`, flag `_migrated_mon0`).
- Rely on `ServerAliveInterval/CountMax` + `ExitOnForwardFailure=yes` for disconnect detection instead of `-M`.
- `TunnelController` detects the `_FWD_FAIL` string ("remote port forwarding failed") and `_SSH_255` ("exited with error status 255") in process output and fails fast with `verify_fwd_fail` / `verify_ssh255` instead of looping.

### #2 — Fake "connected" state without real verification  *(FIXED)*
**Symptom:** UI showed connected when the SOCKS port was open but nothing actually tunneled.
**Fix:** added a real SOCKS5 handshake probe (`socks5_handshake_ok`) and a verify state machine (`_verify_step`) before declaring `on`; plus periodic `_health_check`.

### #3 — Local SOCKS port still occupied on quick reconnect  *(FIXED)*
**Symptom:** reconnecting immediately failed because the previous ssh child still held the local `-D` port.
**Fix:** `_ensure_local_port_free()` waits for the port to free and, if needed, `fuser -k <port>/tcp` kills the holder before starting.

### #4 — Multiple tunnels piling up / memory growth  *(FIXED)*
**Symptom:** repeated connects spawned overlapping autossh processes.
**Fix:** `start()` stops any existing process first; `_cleanup_orphan_tunnels()` kills tracked leftover PIDs from prior runs; `tracked_pids` persisted in config.

### #5 — gsettings reports success but proxy didn't actually change  *(FIXED)*
**Symptom:** "set SOCKS" / "automatic" logged success but the GNOME proxy mode didn't change (e.g. missing D-Bus session).
**Fix:** `_gsettings_set` inspects stderr for "failed to commit"; `set_system_socks` / `set_system_proxy_auto` read back the mode via `_gsettings_get` and return an explicit failure if it didn't stick.

### #6 — Normal internet broken while tunnel is OFF (terminal proxy)  *(FIXED)*
**Symptom:** terminal env-var proxy persisted after disconnect, breaking the shell's internet.
**Fix:** `clear_terminal_proxy()` writes `unset` lines on disconnect; rc hook sources the file so it follows tunnel state. Hint text warns that already-open terminals need `source ~/.bashrc`.

### #7 — App rename losing user data / duplicating autostart / stale .bashrc block  *(FIXED)*
**Symptom (anticipated during the Manager→Proxy rename):** changing the slug would orphan the old config dir, leave an old `.desktop` autostart entry, and leave an old managed block in `.bashrc`.
**Fix:** migration lists for config dirs, autostart files, and rc markers (see Invariant #1). All recognized and migrated/removed automatically.

### #8 — Missing HTTP/HTTPS/FTP clearing on connect  *(FIXED, user-requested)*
**Symptom:** in GNOME manual mode, pre-existing HTTP/HTTPS/FTP proxies stayed active alongside SOCKS.
**Fix:** `set_system_socks` clears those three schemas on connect; `set_system_proxy_auto` clears them again on revert.

### Minor note (low priority, currently harmless)
- `_on_tunnel_failed` uses a default monitor port string of `"1086"` when formatting the `verify_fwd_fail` message, while the rest of the code defaults monitor to `"0"`. This only affects the *text* of an error message (the `{m}` placeholder) and does not affect behavior. If touched, align it to read the profile's actual `mon_port` or `"0"`.

---

## 11. Packaging (`pyproject.toml`)

- `name = "ssh_tunnel_proxy"`, `version = "1.2.2"`.
- `requires-python = "==3.13.*"`.
- Deps pinned, including PyInstaller (`pyinstaller==6.20.*`, `pyinstaller-hooks-contrib==2026.*`) and PyQt5 (`pyqt5==5.15.*` + `pyqt5-qt5`, `pyqt5-sip`). Build artifact is intended to be a PyInstaller bundle.
- Commented-out Iranian PyPI mirror indexes (runflare / parspack / liara) are present for users behind restricted networks — leave them as commented hints.

---

## 12. How to use this file in a new conversation

When the user attaches this file and reports a new problem:
1. Reconstruct the relevant layer from sections 3–8 before reading code.
2. Check sections 9 (Invariants) and 10 (Known Issues) — the new symptom may be a regression of a solved bug, or adjacent to one.
3. If the user also attaches `main.py`, prefer the actual source over this summary where they disagree (this file can drift; code is ground truth). If only this file is attached and a precise line is needed, ask for the current `main.py`.
4. Keep the single-file structure and the documented invariants intact unless the user explicitly asks to refactor.