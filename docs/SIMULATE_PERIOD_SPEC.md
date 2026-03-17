# Simulate-period — Implementation spec

This document defines the contract and behaviour of **POST /api/agrienergy/simulate-period** for historical simulation over a time range. It extends the existing one-shot **POST /simulate** by iterating over a series of timesteps, running the same algorithm and PV/shadow logic per step.

---

## 1. Purpose

- **Input**: A time window (start, end), tracker and parcel (by spec or by entity id), and a **time series of weather** (and optionally vegetative data) for that period.
- **Process**: For each timestep (e.g. every 15 min): build context from the series (with **state carry-over**: previous step’s tilt/azimuth → current step’s `context.tracker`) → resolve algorithm → compute tilt/azimuth → run PV + shadow → optional Intelligence call for biology.
- **Output**: Time series of `{ timestamp, tilt, azimuth, expected_power_w, shadow_area_m2, stress_index? }` plus optional aggregates.

---

## 2. Request: POST /api/agrienergy/simulate-period

### 2.1 Body (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tracker_id` | string | no* | AgriEnergyTracker entity ID (URN). If provided, backend loads tracker from Orion (tenant from auth) and uses its `activeAlgorithm`, geometry, location. *Required if `tracker` is omitted.* |
| `tracker` | object | no* | Inline tracker spec (same shape as `/simulate`: id, panel_width, panel_length, capacity_w, min_tilt, max_tilt, lat, lon, parent_parcel_id). *Required if `tracker_id` is omitted.* |
| `parcel_id` | string | no* | AgriParcel entity ID. If provided, backend loads parcel from Orion. *Required if `parcel` is omitted.* |
| `parcel` | object | no* | Inline parcel spec (id, slope, aspect). *Required if `parcel_id` is omitted.* |
| `start` | string | yes | Start of period (ISO 8601 datetime, e.g. `2026-03-01T00:00:00Z`). |
| `end` | string | yes | End of period (ISO 8601 datetime, exclusive or inclusive to be defined). |
| `resolution_min` | int | no | Timestep in minutes. Default **15**. Max e.g. 60 to avoid huge responses. |
| `data_source` | string | yes | `"payload"` (v1): client sends the series in the request. Future: `"platform"` (backend fetches from timeseries/DataHub by entity ids). |
| `series` | array | yes when `data_source: "payload"` | Array of objects: `{ "timestamp": "ISO8601", "ghi": float, "dni": float, "dhi": float, "temperature"?: float, ... }`. Optional keys (e.g. soil_moisture, leaf_temperature) can be used for context/Intelligence if present. |
| `include_biology` | bool | no | If true, call Intelligence per timestep (shadow + telemetry) and add `stress_index` (and other scalars) to context and to output. Default **false** for v1 (simpler, no dependency on Intelligence latency). |

**Rules:**

- Exactly one of `(tracker_id, parcel_id)` or `(tracker, parcel)` must be provided. If `tracker_id`/`parcel_id` are used, the request must be authenticated and tenant is taken from JWT; backend uses Context Broker to load entity.
- `start` < `end`. Timestamps in `series` (when `data_source: "payload"`) should fall within [start, end]; backend subsamples or uses nearest-neighbour per `resolution_min`.
- **Strict limit when `include_biology: true`**: To avoid gateway timeouts (N synchronous HTTP calls to Intelligence), the number of simulated steps **must not exceed 96** when `include_biology` is true (e.g. 1 day at 15 min). If the requested range would produce more than 96 steps, the backend **must respond with HTTP 400** and a clear message (e.g. `"include_biology is limited to 96 steps (e.g. 1 day at 15 min); reduce range or resolution or set include_biology to false"`). Do **not** auto-disable `include_biology`; reject the request so the client can decide.

---

## 3. Response

### 3.1 Body (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `series` | array | One object per timestep (see below). |
| `summary` | object | Optional: `total_energy_wh`, `mean_stress`, `min_tilt`, `max_tilt`, etc. |

**Series item:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601. |
| `tilt` | float | Algorithm output (degrees). |
| `azimuth` | float | Algorithm output (degrees), default 180 if single-axis. |
| `expected_power_w` | float | PV output for this timestep. |
| `shadow_area_m2` | float | Shadow area (2.5D). |
| `stress_index` | float | Present only if `include_biology: true` and Intelligence returned it. |

---

## 4. Behaviour (backend)

1. **Resolve tracker and parcel**: From `tracker_id`/`parcel_id` (Orion) or from inline `tracker`/`parcel`.
2. **Validate step count**: Compute number of steps = (end − start) / resolution_min. If `include_biology` is true and steps > 96, **return HTTP 400** (include_biology limited to 96 steps). When `include_biology` is false, apply general cap (e.g. 2976); return 400 if exceeded.
3. **Pre-index the input series (mandatory)**  
   Before the time loop, **index** `series` so lookup by timestep is **O(1)** (e.g. dict keyed by normalized timestamp, or sort + bisect). **Do not** linear-scan `series` inside the loop — O(N²) blocks the process.
4. **State carry-over**: Maintain `current_tilt` and `current_azimuth`. Step 0: from tracker entity or 0° / 180°. Each step: set `context["tracker"]["tilt"]` / `azimuth` to these; after algorithm + PV/shadow, update them from the step output.
5. **Per timestep**:
   - Build **context**: weather from the series row (ghi, dni, dhi, temperature, …); tracker state = previous step’s tilt/azimuth (first step: current or 0/180).
   - Resolve **algorithm**: tracker’s `activeAlgorithm` (if from Orion) or default; evaluate rule → tilt (and azimuth if rule returns dict).
   - **PV + shadow**: same as `/simulate` (PVEngine + ShadowEngine) with that tilt/azimuth and weather.
   - If `include_biology`: call Intelligence `evaluate_status` with shadow polygon + telemetry; inject `biology` into context; append `stress_index` (or similar) to output row. On timeout/error: omit or use null for that step.
6. **Response**: Collect all rows into `series`; optionally compute `summary` (e.g. sum expected_power_w * (resolution_min/60) for total_energy_wh).

### 4.1 Mandatory implementation requirements

- **Limit when `include_biology`**: If `include_biology` is true, reject the request with **HTTP 400** when the number of steps exceeds **96** (e.g. 1 day at 15 min). Do not auto-disable `include_biology`; return a clear error message so the client can reduce range/resolution or disable biology. Rationale: N synchronous calls to Intelligence (e.g. 3000 × 50 ms ≈ 150 s) cause gateway timeouts (504).
- **Pre-index series**: Before the loop, index the input `series` (e.g. dict keyed by normalized timestamp, or sort + bisect) so that each timestep lookup is **O(1)**. Linear search per step would be O(N²) and block the process.
- **State carry-over**: Initialise `current_tilt` and `current_azimuth` from the tracker (or 0 / 180 for inline spec). At each step, set `context["tracker"]["tilt"]` and `context["tracker"]["azimuth"]` from these variables; after running the algorithm and PV/shadow, update both from the step output for the next iteration.

---

## 5. Scope (v1)

- **Data source**: Only `data_source: "payload"`. Client provides the historical series; platform-backed fetch is out of scope for v1.
- **Intelligence**: Optional via `include_biology`. If true, same contract as `/notify` (200 ms timeout, fail-safe empty biology). **Strict limit**: max **96 steps** when `include_biology` is true (e.g. 1 day at 15 min). Rationale: 96 × 50 ms ≈ 5 s; 3000 steps would be ~150 s and cause gateway timeout (504). Reject with 400 if the requested range would exceed 96 steps with `include_biology` true. Future: an Intelligence batch endpoint (e.g. `/evaluate_status_batch`) could lift this limit.
- **Auth**: Required when using `tracker_id`/`parcel_id` (tenant from JWT). Optional when using inline `tracker`/`parcel` (no Orion access).
- **Limits**: When `include_biology` is false, cap total steps at a reasonable value (e.g. 2976 for 31 days at 15 min); return 400 if exceeded. When `include_biology` is true, cap at **96** steps (return 400 if more).

---

## 6. References

- One-shot simulation: `POST /simulate` and `SimulationRequest`/`SimulationResponse` in backend.
- Algorithm engine: `AlgorithmEngine.evaluate_rule`, `resolve_orientation`; context build similar to `/notify`.
- Overview: [docs/REFERENCE.md](REFERENCE.md).
