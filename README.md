# Home Assistant integration for CocktailPi

A custom integration for [CocktailPi](https://github.com/alex9849/CocktailPi), built against the
API reverse-engineered in [`docs/api.md`](docs/api.md).

This repo includes a `hacs.json`, so it can be added to HACS as a custom repository, or installed
manually.

## Installation

### HACS (custom repository)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/rizz360/ha-cocktailpi` with category **Integration**.
3. Install "CocktailPi", then restart Home Assistant.

### Manual

Copy `custom_components/cocktailpi/` into your Home Assistant config directory's
`custom_components/` folder, then restart Home Assistant and add the integration via
**Settings → Devices & Services → Add Integration → CocktailPi**.

You'll need the host/port of your CocktailPi instance and a username/password for a user with at
least the `PUMP_INGREDIENT_EDITOR` role (needed to start/stop pumps; `ADMIN` if you also want to
use pump-editing features later).

## What v1 covers

- **Pump monitoring**: a fill-level sensor (mL) and a status sensor (current ingredient + pump
  state) per pump, polled over REST every 30s.
- **Pump control**: each pump is exposed as a `valve` entity — *open* starts the pump, *close*
  stops it — plus one aggregate "All pumps" valve. There are also `pump_up`/`pump_back` entity
  services (target a pump valve) to prime/reverse-prime a pump's tube.
- **Cocktail ordering & progress**: `cocktailpi.order_cocktail` and `cocktailpi.cancel_cocktail`
  services, plus a "Current cocktail" sensor showing the recipe name currently in production
  (state/progress/instruction as attributes) — this reflects orders placed from *anywhere*
  (the CocktailPi touchscreen included), not just from Home Assistant.
- **System info**: CocktailPi's version is attached as the hub device's `sw_version`.

## Architecture notes

- Pump/system state is REST-polled (simple, robust). There's no REST endpoint for "what's
  currently being made" or a pump's live running state — those are WebSocket-push only in the
  CocktailPi backend — so a small STOMP-over-WebSocket client (`ws.py`) runs alongside the
  poller just for those two things. See the "WebSocket" section of `docs/api.md`.
- Because pump running-state also has no REST equivalent, each pump valve's reported open/closed
  state is *optimistic* until the first WS `runningstate` message arrives for that pump, then
  becomes authoritative. The "All pumps" valve has no per-aggregate WS topic, so it's always
  optimistic (`assumed_state`).
- Login uses `remember: true`, which the backend gives a ~10 year token — no token-refresh logic
  is implemented since re-login basically never becomes necessary during normal operation; a 401
  triggers one automatic re-login/retry regardless.
- Pumps are assumed static after startup: a pump added on the CocktailPi side after Home Assistant
  starts won't get entities or a live running-state subscription until the integration reloads.

## Known caveats to revisit

- `docs/api.md` flags a possible bug in the CocktailPi backend's
  `WebSocketSecurityConfig` (an authority-string mismatch that may make the ADMIN-gated WS topics
  unreachable). This integration doesn't touch those topics, so it isn't affected either way — just
  worth knowing about if you extend this further into event-action status/logs.
- Only one CocktailPi instance can be targeted implicitly by the `order_cocktail`/`cancel_cocktail`
  services; with more than one configured, pass `config_entry_id` explicitly.

## Status

This integration has not yet been tested against a live CocktailPi instance or a running Home
Assistant install — it's scaffolded and byte-compiles cleanly, but the config flow, entities,
services, and especially the hand-rolled STOMP WebSocket client (`ws.py`) are unverified. Treat it
as a release candidate, not a working release, until that testing happens.

## TODO before publishing

- Test against a real CocktailPi backend + running HA (config flow, sensors/valves, services, WS
  client).
- Add an icon/logo via [home-assistant/brands](https://github.com/home-assistant/brands) if this
  goes into HACS's default repository list.
