# Transfer Switch

This page covers features specific to the Jackery Smart Transfer Switch (JA-TS02A / model HTO785A).

## Overview

The Smart Transfer Switch bridges the utility grid and connected Jackery battery devices. It can automatically switch between grid and battery power, manage charging schedules, and monitor per-circuit power consumption.

## Working Modes

The Transfer Switch operates in one of three working modes, controlled by the **Working Mode** select entity.

| Mode | `en` Value | Description |
|------|-----------|-------------|
| Automatic Charging | `0` | Automatically manages charging from the grid based on backup reserve |
| Scheduled Tasks | `1` | Uses configured charge/discharge plans to control when to charge or discharge |
| Self Consumption | `2` | Prioritizes battery and solar output; charges from the grid only when needed |

Each mode has its own backup reserve percentage (the minimum battery level held in reserve for outages). The backup reserve for the currently active mode is shown in the **Backup Reserve** number entity and can be adjusted there directly.

See [Charging Plans](Charging-Plans) for details on setting up scheduled charge/discharge plans used by Scheduled Tasks mode.

## Grid / Station Toggle

The **Grid / Station** switch selects whether the home loads are powered by the utility grid or by the connected battery devices. Toggling this switch does not change the working mode.

## UPS Mode

The **UPS Mode** switch enables approximately 20ms grid-to-battery switchover on a power interruption. When UPS Mode is enabled, the **UPS Mode** binary sensor also reflects the active state.

## Force Charge

The **Force Charge** switch forces the battery to charge from the grid regardless of the current working mode or scheduled plans. Useful for quickly topping up before an expected outage.

## Circuits

The Transfer Switch monitors and controls individual circuits in the connected electrical panel.

### Circuit Entities

For each logical circuit, the integration creates:

- A **power sensor** showing current power consumption in watts.
- An **on/off switch** to toggle the circuit breaker.

Circuit names are decoded from the device configuration. Circuits without a configured name fall back to their index number.

### Split-Phase Pairs

240V circuits use two legs (split-phase). The integration automatically detects paired legs using the `sph` cross-reference index and combines them into a single entity. The combined power sensor reports the sum of both legs. Toggling the combined switch toggles both legs together.

### Circuit Data Availability

Circuit data is not included in the HTTP property snapshot. It is queried on startup via the persistent MQTT connection. Entities are pre-seeded from that initial query so they are available immediately after setup. Updates are received from the device via the same persistent MQTT connection as circuit states change.

### Circuit Physical Status

The Jackery Transfer Switch does *NOT* monitor or show the physical status of the circuit breakers. If the breaker physically trips the Transfer Switch will happily show the circuit as active, because in the software it technically is. For important loads like refrigerators it is probably still prudent to have a power monitoring plug of some kind for redundancy.

## AC1 and AC2 Battery Slots

The Transfer Switch has two AC output ports (AC1 and AC2) that can each connect to a Jackery portable power station. The integration creates a set of diagnostic sensors for each connected device.

See [Sensors - AC1 and AC2 Battery Slots](Sensors#ac1-battery-slot) for the full sensor list.

### Battery Pack Add-ons

Each connected portable can have up to five add-on battery packs. The integration creates individual battery level sensors for each detected pack (`AC1 Pack 1 Battery` through `AC1 Pack 5 Battery`). Each sensor includes the pack serial number as a state attribute.

Pack sensors only appear when the pack is physically connected. After a pack is first plugged in it can take 24 hours or more before the sensor appears. Re-adding the base device to the app triggers add-on packs being added immediately to the app/integration.

### Charging Status When Connected

When a portable is connected to the Transfer Switch, the portable's own Battery Status sensor reports Idle even when it is actively charging. The authoritative charging status is the **AC1 Battery Status** or **AC2 Battery Status** sensor on the Transfer Switch device.

## Fault Diagnostics

The Transfer Switch reports fault conditions through the `fz` property object. The integration flattens these into individual entities.

### Multi-State Fault Sensors

| Sensor | States |
|--------|--------|
| AC1 Error Code | OK or error code F1-FF |
| AC1 Temperature Alarm | OK / High Temperature / Low Temperature |
| AC2 Error Code | OK or error code F1-FF |
| AC2 Temperature Alarm | OK / High Temperature / Low Temperature |
| Mains Power Fault | OK / Not Connected / Abnormality |
| Module Overload | OK / Mains Power Overload / Energy Storage Overload |

### Binary Fault Sensors

| Sensor | Description |
|--------|-------------|
| AC1 Communication Fault | AC1 communication fault |
| AC2 Communication Fault | AC2 communication fault |
| Cover Open | Cover open fault |
| Emergency Stop | Emergency stop fault |
| RTC Fault | Real-time clock fault |
| Temperature Fault | NTC temperature fault |

Fault entities are created when the device reports the `fz` sub-object. All fault entities are in the diagnostic entity category.
