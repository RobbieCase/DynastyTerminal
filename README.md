# Dynasty Terminal

A browser dynasty fantasy football terminal: live league sync, player intelligence, and a backtested
usage signal. Pulls live data, models it, surfaces mispricings — but football-statistics-forward, not finance-skinned.

See `PROJECT_OUTLINE.md` for the current system map, weakest points, and prioritized roadmap.

## Validation

Run the local app/data contract checks before pushing:

```bash
node scripts/validate.mjs
```

Run live ESPN/Sleeper smoke checks when network access is available:

```bash
node scripts/validate.mjs --network
```
