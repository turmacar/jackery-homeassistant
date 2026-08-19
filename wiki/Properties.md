# Device Properties Reference

This page documents the raw property keys used by the Jackery protocol, what they mean, and whether the integration maps them to Home Assistant entities.

## Protocol Overview

Device data arrives through two channels:

- **HTTP polling** - The integration periodically fetches a property snapshot from the Jackery API. This covers most sensor values.
- **MQTT** - A persistent connection receives real-time property updates pushed by the device. Some data (circuits, plans) is only available via MQTT queries.

Commands (writing values) are sent via MQTT. It seems more stable to use the persistent connection that is already broadcasting data.

---

## Transfer Switch Properties

Properties marked **MQTT only** are not included in the HTTP snapshot and require an explicit MQTT query.

| Property | Type | Description | Protocol | Integration Entity |
|----------|------|-------------|----------|--------------------|
| `ac1` | object | Battery Slot 1 (see sub-object below) | HTTP | AC1 sensors |
| `ac2` | object | Battery Slot 2 (see sub-object below) | HTTP | AC2 sensors |
| `autoDt` | int | Auto mode backup reserve (%) | HTTP | Not mapped** |
| `cds` | list | Charge/discharge plan list | HTTP | Plan switches |
| `cdsDt` | int | Scheduled mode backup reserve (%) | HTTP | Not mapped** |
| `cep` | object | Currently executing plan | HTTP | Active Plan sensor |
| `cir` | list | Circuit list (see sub-object below) | MQTT only | Circuit sensors/switches |
| `de` | int | Battery discharge today (Wh cumulative) | HTTP | Not mapped* |
| `ddt` | int | Default/current backup reserve (%) | HTTP | Backup Reserve number |
| `dg` | int | Grid consumption today (Wh cumulative) | HTTP | Not mapped* |
| `dh` | int | House consumption today (Wh cumulative) | HTTP | Not mapped* |
| `ds` | int | Solar generation today (Wh cumulative) | HTTP | Not mapped* |
| `dt` | int | Legacy backup reserve (%) | HTTP | Not mapped** |
| `en` | int | Working mode (0=Auto, 1=Scheduled, 2=Self) | HTTP | Working Mode select |
| `fz` | object | Fault zone (see sub-object below) | HTTP | Fault sensors |
| `ip` | int | Input power (W) | HTTP | Total Input Power sensor |
| `op` | int | Output power (W) | HTTP | Output Power sensor |
| `ot` | int | Remaining output time | HTTP | Remaining Output Time sensor |
| `pss` | int | Power system state (0=Grid, 1=Station) | HTTP | Power System State sensor + Grid/Station switch |
| `rb` | int | Remaining battery (%) | HTTP | Remaining Battery sensor |
| `rc` | int | Rapid/force charging (0=off, 1=on) | HTTP | Force Charge switch |
| `selfDt` | int | Self Consumption mode backup reserve (%) | HTTP | Not mapped** |
| `storm` | list | Weather/storm events | MQTT only | Not mapped** |
| `ups` | int | UPS mode (0=off, 1=on) | HTTP | UPS Mode switch + binary sensor |
| `wps` | int | Weather Protection System (0=off, 1=on) | HTTP | Not mapped** |

### AC Slot Sub-Object (ac1 / ac2)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `acpsp` | int | Solar panel power (/10 = W) | Not mapped (per-slot solar) |
| `bi` | int | Battery connected (0=no, 1=yes) | AC1/AC2 Connected sensor |
| `bp` | list | Add-on battery packs (see BatteryPack below) | AC1/AC2 Battery Packs count + per-pack sensors |
| `bs` | int | Battery status (0=Idle, 1=Charging, 2=Discharging, 3=Fault) | AC1/AC2 Battery Status sensor |
| `ip` | int | Input power (W) | AC1/AC2 Input Power sensor |
| `it` | int | Time to full | AC1/AC2 Time to Full sensor |
| `mc` | int | Model code | Not mapped |
| `op` | int | Output power (W) | AC1/AC2 Output Power sensor |
| `ot` | int | Remaining output time | AC1/AC2 Remaining Time sensor |
| `rb` | int | Remaining battery (%) | AC1/AC2 Battery Level sensor |
| `sn` | str | Serial number | Not mapped (device attribute) |
| `ss` | int | Solar status | Not mapped |
| `trb` | int | Total battery % across station + all packs combined | Not mapped |

### Add-on Battery Pack Sub-Object (bp items in ac1/ac2)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `rb` | int | Pack remaining battery (%) | AC1/AC2 Pack N Battery sensor |
| `sn` | str | Pack serial number | State attribute on pack sensor |

### Fault Zone Sub-Object (fz)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `bs1` | int | AC1 communication fault | AC1 Communication Fault binary sensor |
| `bs2` | int | AC2 communication fault | AC2 Communication Fault binary sensor |
| `ec1` | int | AC1 error code (0=OK, non-zero=F1-FF) | AC1 Error Code sensor |
| `ec2` | int | AC2 error code (0=OK, non-zero=F1-FF) | AC2 Error Code sensor |
| `es` | int | Emergency stop | Emergency Stop binary sensor |
| `gs` | int | Mains power fault (0=OK, 1=not connected, 2=abnormal) | Mains Power Fault sensor |
| `loc` | str | Line overload | Not mapped |
| `moc` | int | Module overload (0=OK, 1=mains overload, 2=storage overload) | Module Overload sensor |
| `ntc` | int | NTC temperature fault | Temperature Fault binary sensor |
| `ol` | int | Cover open fault | Cover Open binary sensor |
| `rtc` | int | RTC fault (observed in live data; not in APK model) | RTC Fault binary sensor |
| `ta1` | int | AC1 temperature alarm (0=OK, 1=high, 2=low) | AC1 Temperature Alarm sensor |
| `ta2` | int | AC2 temperature alarm (0=OK, 1=high, 2=low) | AC2 Temperature Alarm sensor |

### Circuit Sub-Object (cir items)

| Field | Type | Description |
|-------|------|-------------|
| `idx` | int | Circuit index (0-11) |
| `nm` | str | Circuit name (base64-encoded) |
| `pc` | int | Power consumption (W) |
| `pr` | int | Priority |
| `sph` | int | Split-phase partner index (-1 = not paired) |
| `sph_pc` | int | Split-phase partner power consumption |
| `sw` | int | Switch state (0=off, 1=on) |

---

## Portable Station Properties

| Property | Type | Description | Protocol | Integration Entity |
|----------|------|-------------|----------|--------------------|
| `accd` | int | AC output countdown remaining | HTTP | Not mapped |
| `acdt` | int | AC delay timer config | HTTP | Not mapped |
| `acip` | int | AC input power (W) | HTTP | AC Input Power sensor |
| `acmode` | int | AC output mode (0=normal, 1=timer) | HTTP | Not mapped |
| `acohz` | int | AC output frequency (Hz) | HTTP | AC Output Frequency sensor |
| `acov` | int | AC output voltage bus (/10 = V) | HTTP | AC Output Voltage (Bus) sensor |
| `acov1` | int | AC outlet voltage (/10 = V) | HTTP | AC Output Voltage (Outlet) sensor |
| `acpss` | int | AC pass-through status (0=inactive) | HTTP | Not mapped |
| `acpsp` | int | Solar panel power (/10 = W) | HTTP | Solar Panel Input Power sensor |
| `ast` | int | Auto shutdown timer (minutes) | HTTP | Auto Shutdown number |
| `bc` | int | Battery cutoff (%) | HTTP | Not mapped |
| `box` | int | Connected to Transfer Switch (0/1) | HTTP | Transfer Switch Connected binary sensor (not mapped yet) |
| `bpc` | int | Battery pack capacity/config | HTTP | Not mapped |
| `bs` | int | Battery status (0=Idle, 1=Charging, 2=Discharging, 3=Fault) | HTTP | Battery Status sensor |
| `bt` | int | Battery temperature (/10 = C) | HTTP | Battery Temperature sensor |
| `cip` | int | DC/solar input power (W) | HTTP | DC Input Power sensor |
| `cl` | int | Charge limit (%) | HTTP | Not mapped |
| `cs` | int | Charge speed | HTTP | Charge Speed select |
| `dhg_recall` | int | Discharge memory (0=off, 1=on) | HTTP | Not mapped |
| `dl` | int | Discharge limit (%) | HTTP | Not mapped |
| `dt` | int | Backup reserve (%) | HTTP | Not mapped |
| `ec` | int | Error code | HTTP | Error Code sensor |
| `en` | int | Working mode (reported when box=1) | HTTP | Not mapped |
| `iac` | int | Input AC status | HTTP | Not mapped |
| `iacPw` | int | Input AC power detail (W) | HTTP | Not mapped |
| `idc` | int | Input DC status | HTTP | Not mapped |
| `ip` | int | Total input power (W) | HTTP | Total Input Power sensor |
| `ipalPw` | int | Input panel/solar power (W) | HTTP | Not mapped |
| `it` | int | Time to full (/10 = hours) | HTTP | Time to Full sensor |
| `lm` | int | Light mode (0=off, 1=low, 2=high, 3=sos) | HTTP | Light Mode select |
| `lps` | int | Battery protection (0=full, 1=eco) | HTTP | Battery Protection select |
| `oac` | int | AC output active (0/1) | HTTP | AC Output binary sensor + switch |
| `oac2` | int | Second AC output (240V) | HTTP | Not mapped |
| `oacPw` | int | AC output power per-port (W) | HTTP | Not mapped |
| `oact` | int | AC output countdown | HTTP | Not mapped |
| `odc` | int | DC output (0/1) | HTTP | DC Output binary sensor + switch |
| `odcc` | int | DC car output (0/1) | HTTP | DC Car Output binary sensor + switch |
| `odcct` | int | DC car countdown | HTTP | Not mapped |
| `odcPrio` | int | DC output priority (0/1) | HTTP | Not mapped |
| `odcPrioSoc` | int | DC priority SOC threshold (%) | HTTP | Not mapped |
| `odct` | int | DC output countdown | HTTP | Not mapped |
| `odcu` | int | USB output (0/1) | HTTP | USB Output binary sensor + switch |
| `odcut` | int | USB countdown | HTTP | Not mapped |
| `op` | int | Output power (W) | HTTP | Output Power sensor |
| `opalPw` | int | Output panel power (W) | HTTP | Not mapped |
| `ot` | int | Remaining output time (/10 = hours) | HTTP | Remaining Output Time sensor |
| `outPrio` | int | Output priority (0/1) | HTTP | Not mapped |
| `pal` | int | Power alarm (0/1) | HTTP | Power Alarm binary sensor |
| `pc` | int | Parallel connection (0=none, 1=charge, 2=discharge) | HTTP | Parallel Connection sensor |
| `pm` | int | Energy saving mode | HTTP | Energy Saving number |
| `pmb` | int | Outlets active (0/1) | HTTP | Outlets Active binary sensor |
| `pss` | int | Power system state | HTTP | Not mapped (TS-side sensor) |
| `rb` | int | Remaining battery (%) | HTTP | Remaining Battery sensor |
| `sfc` | int | Super fast charge (0/1) | HTTP | Super Fast Charge switch |
| `sltb` | int | Screen timeout | HTTP | Screen Timeout number |
| `ss` | int | Solar status (0=normal, 1=high V, 2=low V, 3=both) | HTTP | Solar Type sensor |
| `ta` | int | Temperature alarm (0/1) | HTTP | Temperature Alarm binary sensor |
| `tmt` | int | Auto shutdown timer value | HTTP | Not mapped (use `ast`) |
| `tp` | int | Temperature protection (0/1) | HTTP | Temperature Protection binary sensor |
| `tt` | int | Temperature threshold (when box=1) / task type (in plans) | HTTP | Not mapped |
| `ups` | int | UPS mode (0/1) | HTTP | UPS Mode binary sensor + switch |
| `usba1` | int | USB-A port 1 power (W) | HTTP | Not mapped |
| `usba2` | int | USB-A port 2 power (W) | HTTP | Not mapped |
| `usba3` | int | USB-A port 3 power (W) | HTTP | Not mapped |
| `usbc1` | int | USB-C port 1 power (W) | HTTP | Not mapped |
| `usbc2` | int | USB-C port 2 power (W) | HTTP | Not mapped |
| `usbc3` | int | USB-C port 3 power (W) | HTTP | Not mapped |
| `wss` | int | WiFi signal status | HTTP | Not mapped |

---

## Notes

- `*` - Planned for a future update.
- `**` - Does not appear to be a functional feature, and/or not found in the Jackery app.
- "Not mapped" - exists in the protocol but are not yet a priority.
- The `bs` (Battery Status) property on a portable reports `0` (Idle) when the device is connected to and managed by a Transfer Switch. Use the Transfer Switch's `ac1.bs` / `ac2.bs` instead. See [Portable Devices](Portable-Devices#transfer-switch-connection).
- Some portable properties (`en`, `dt`, `dl`, `cl`) only appear or become meaningful when `box=1` (connected to a Transfer Switch).
- The `sltb` property is the read key for screen timeout; the write command uses a different key (`slt`).
