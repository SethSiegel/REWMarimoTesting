# CLAUDE.md - Limit Tester

This file provides guidance to Claude Code when working with code in this directory.

## CRITICAL REQUIREMENT

Complete thorough problem-solving with clarifying questions. Skip flattery. Lead with key information, follow with supporting details. Cite all sources. Explicitly flag any generated/unsupported data - use it only for illustration when real data would obscure the point.

Never use emojis - and delete any that you find in the codebase.

## Usage

Before making any changes to files in this directory:
1. Use the Task tool with subagent_type="web-api-visualizer"
2. Provide the agent with context about the changes you plan to make
3. Let the agent guide the implementation

## Project Overview

The limit-tester directory is part of the ESR Venue Controls system and is responsible for monitoring and visualizing amplifier telemetry data, including power consumption, wattage, temperature, and signal levels from LEA amplifiers via WebSocket connections.

## Key Files

- **server.py**: Flask + Socket.IO server bridging the browser frontend to the LEA monitor backend
- **lea_monitor.py**: Real LEA amplifier monitoring -- WebSocket connection, notification processing, CSV logging
- **lea_monitor_stub.py**: Stub implementation for testing without hardware
- **templates/index.html**: Web interface template
- **static/js/app.js**: Frontend logic -- Socket.IO event handlers, chart rendering, UI state
- **static/css/style.css**: Styles
- **logs/**: CSV output directory

## Data Recording Strategy

CSV recording is time-driven, not event-driven. A periodic asyncio task writes one row every 100ms regardless of incoming LEA notifications. This ensures continuous, gap-free data.

Key principles:
- **Carry forward last known values** -- if the LEA doesn't include a field in a notification, the physical quantity hasn't changed. Use the last received value, not zero.
- **Per-field staleness timeout (2s)** -- if a field hasn't been updated by the LEA in 2 seconds, zero it out. Stale carry-forward would be misleading.
- **Empty for never-received** -- if the LEA has never sent a field for a channel, record empty (not zero) to distinguish "no data" from "measured zero."
- **`data_source` column** -- `live` means a new notification arrived since the last row; `fill` means no new data (carried forward).
- **Impedance from hardware only** -- use the LEA's `measuredImpedance` from `/amp/channels/{N}/loadMonitor`. Do not calculate impedance from voltage/current on the frontend.

LEA notification behavior: the LEA does not send all fields in every notification. Voltage, current, dB level, impedance, and status may arrive separately at different rates. Some fields (like `level_amps`) may be omitted entirely under certain drive conditions. The backend emits current=0 and power=0 when voltage is present but current is absent, so the frontend always receives all three metrics together.

## Development

```bash
Run the server
./run.sh
```
and make modifications to the run.sh script if needed.

IMPORTANT - DON'T start the server yourself - always ask the user to run the server themself (providing the command needed to do so in a separate terminal window) - so the user can have better control.

## Remember

Never work on this directory without using the web-api-visualizer agent. This ensures consistent implementation patterns for amplifier metrics visualization and WebSocket data handling.

ALWAYS EXPLAIN EACH CODING CHANGE.