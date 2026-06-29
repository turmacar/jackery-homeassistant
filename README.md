> This is a community-maintained project. Issue responses may be slow, but pull requests are welcome! Reasonable PRs will be reviewed, tested, and merged. Thank you for contributing!

> **Known issue:** This integration currently does not support accounts registered in the EU.

# Jackery Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40theak-blue.svg)](https://github.com/theak)
[![version](https://img.shields.io/badge/version-1.1.1-blue.svg)](https://github.com/theak/jackery-homeassistant)

Custom Home Assistant integration for monitoring and controlling Jackery portable power stations. This integration provides real-time sensor data for your Jackery devices along with writable controls for supported settings and charging plans on supported Jackery Plus models.

## Features

- 🔋 **Battery Monitoring**: Track remaining battery percentage, battery temperature, and battery status
- ⚡ **Power Monitoring**: Monitor total input, AC input, DC input, output power, AC output voltage, and AC output frequency
- ⏱️ **Time Tracking**: View time to full charge, remaining output time, and the last successful refresh timestamp
- 🔌 **Output Status**: Binary sensors for AC, DC, DC car, and USB output status where supported by the device
- 🎛️ **Device Controls**: Writable switches, selects, and number entities for supported Jackery settings
- 📅 **Charging Plans**: Charging-plan switch, time window, and repeat schedule for supported Jackery Plus devices
- 🏠 **Smart Transfer Switch**: Grid/Station toggle, UPS mode, force charge, working mode, backup reserve, circuit control, fault diagnostics, and scheduled plan management
- ⚡ **Circuit Monitoring**: Per-circuit power sensors and on/off switches with automatic split-phase pair combining
- 🃏 **Lovelace Cards**: Custom Lovelace cards for easier configuration and management of certain entities.
- 🔧 **HA Services**: `jackery.create_plan`, `jackery.update_plan`, and `jackery.delete_plan` for automation-driven Transfer Switch plan management

## Supported Sensors

### Regular Sensors

| Sensor                     | Description                                                           | Unit     |
| -------------------------- | --------------------------------------------------------------------- | -------- |
| Remaining Battery          | Current battery level                                                 | %        |
| Battery Temperature        | Battery temperature                                                   | °C       |
| Battery Status             | Idle, Charging, Discharging, or Fault                                 | text     |
| Output Power               | Current power output                                                  | W        |
| Total Input Power          | Current total power input                                             | W        |
| AC Input Power             | Current AC input power                                                | W        |
| DC Input Power             | Current DC/car input power                                            | W        |
| Solar Panel Input Power    | Current Solar Panel input power                                       | W        |
| Time to Full               | Estimated time to full charge                                         | hours    |
| Remaining Output Time      | Estimated remaining runtime                                           | hours    |
| AC Output Voltage (Bus)    | AC output voltage on the internal bus                                 | V        |
| AC Output Voltage (Outlet) | AC output voltage at the outlet terminals                             | V        |
| AC Output Frequency        | Current AC output frequency                                           | Hz       |
| Error Code                 | Reported device error code                                            | integer  |
| Battery Connected          | Whether an external battery pack is connected                         | Yes/No   |
| Power System State         | Power supplied by Grid or Station (batteries/solar)                   | text     |
| Solar Type                 | None / High Voltage / Low Voltage / High & Low Voltage                | text     |
| Parallel Connection        | None / Charge / Discharge                                             | text     |
| UTC offset                 | Timezone offset in hours                                              | integer  |
| Last Updated               | Timestamp of last successful data refresh                             | ISO 8601 |
| Scheduled Plans            | Number of active scheduled plans (Transfer Switch)                    | integer  |
| Mains Power Fault          | OK / Not Connected / Abnormality (Transfer Switch)                    | text     |
| AC1 Error Code             | OK or error code (F1–FF) (Transfer Switch)                            | text     |
| AC2 Error Code             | OK or error code (F1–FF) (Transfer Switch)                            | text     |
| AC1 Temperature Alarm      | OK / High Temperature / Low Temperature (Transfer Switch)             | text     |
| AC2 Temperature Alarm      | OK / High Temperature / Low Temperature (Transfer Switch)             | text     |
| Module Overload            | OK / Mains Power Overload / Energy Storage Overload (Transfer Switch) | text     |
| Active Plan                | Currently executing scheduled plan (Transfer Switch)                  | text     |
| Circuit *{name}* Power     | Per-circuit power consumption (Transfer Switch)                       | W        |
| AC1 Battery Level          | Battery level of device connected to AC1 (Transfer Switch)            | %        |
| AC1 Output Power           | Output power from AC1 (Transfer Switch)                               | W        |
| AC1 Input Power            | Input power to AC1 (Transfer Switch)                                  | W        |
| AC1 Remaining Time         | Estimated remaining runtime for AC1 (Transfer Switch)                 | hours    |
| AC1 Time to Full           | Estimated time to full charge for AC1 (Transfer Switch)               | hours    |
| AC1 Battery Status         | Battery state of AC1 (Transfer Switch)                                | text     |
| AC1 Connected              | Whether a battery device is connected to AC1 (Transfer Switch)        | Yes/No   |
| AC1 Battery Packs          | Number of add-on battery packs on AC1 (Transfer Switch)               | integer  |
| AC2 Battery Level          | Battery level of device connected to AC2 (Transfer Switch)            | %        |
| AC2 Output Power           | Output power from AC2  (Transfer Switch)                              | W        |
| AC2 Input Power            | Input power to AC2  (Transfer Switch)                                 | W        |
| AC2 Remaining Time         | Estimated remaining runtime for AC2  (Transfer Switch)                | hours    |
| AC2 Time to Full           | Estimated time to full charge for AC2  (Transfer Switch)              | hours    |
| AC2 Battery Status         | Battery state of AC2  (Transfer Switch)                               | text     |
| AC2 Connected              | Whether a battery device is connected to AC2 (Transfer Switch)        | Yes/No   |
| AC2 Battery Packs          | Number of add-on battery packs on AC2  (Transfer Switch)              | integer  |

### Binary Sensors (ON/OFF)

| Sensor                     | Description                                |
|----------------------------|--------------------------------------------|
| AC Output                  | AC output status                           |
| DC Output                  | Combined DC output status                  |
| DC Car Output              | DC car port output status                  |
| USB Output                 | USB output status                          |
| Temperature Alarm          | Device temperature alarm status            |
| Temperature Protection     | Device temperature protection status       |
| Power Alarm                | Device power/protection alarm              |
| UPS Mode                   | Device UPS mode status                     |
| Outlets Active             | Whether any device outlets are active      |
| Transfer Switch Connected  | Device is connected to a Transfer Switch   |
| AC Pass-through            | AC power is being passed through           |
| Emergency Stop             | Emergency stop fault (Transfer Switch)     |
| AC1 Communication Fault    | AC1 communication fault (Transfer Switch)  |
| AC2 Communication Fault    | AC2 communication fault (Transfer Switch)  |
| Cover Open                 | Cover open fault (Transfer Switch)         |
| Temperature Fault          | NTC temperature fault (Transfer Switch)    |
| RTC Fault                  | Real-time clock fault (Transfer Switch)    |

**Note:** Different Jackery device models may report different combinations of DC output sensors. Some models use a combined `odc` parameter while others use separate `odcc` and `odcu` parameters. The integration hides the combined DC entity when split USB/car output keys are available.

## Supported Controls

The integration creates writable entities only when the corresponding properties are reported by the device.

### Switches

| Entity            | Description                                                            |
|-------------------|------------------------------------------------------------------------|
| AC Output         | Toggle AC output                                                       |
| DC Output         | Toggle combined DC output                                              |
| DC Car Output     | Toggle DC car output                                                   |
| USB Output        | Toggle USB output                                                      |
| Super Fast Charge | Toggle super fast charge mode                                          |
| UPS Mode          | Toggle UPS mode                                                        |
| Charging Plan     | Enable or disable charging plans                                       |
| Grid / Station    | Toggle between grid power and station power (Transfer Switch)          |
| Force Charge      | Force battery to charge from grid regardless of mode (Transfer Switch) |
| Circuit *{name}*  | Toggle individual circuits on/off (Transfer Switch)                    |
| Plan *{name}*     | Toggle individual scheduled plans (Transfer Switch)                    |

### Selects

| Entity               | Options                                                                       |
|----------------------|-------------------------------------------------------------------------------|
| Light Mode           | `off`, `low`, `high`, `sos`                                                   |
| Charge Speed         | `fast`, `mute`                                                                |
| Battery Protection   | `full`, `eco`                                                                 |
| Working Mode         | `Automatic Charging`, `Scheduled Tasks`, `Self Consumption` (Transfer Switch) |
| Charging Plan Repeat | `Everyday`, `Weekdays`, `Weekends`, `Once`                                    |

### Numbers

| Entity         | Description                                              | Unit    |
|----------------|----------------------------------------------------------|---------|
| Auto Shutdown  | Auto shutdown delay                                      | minutes |
| Energy Saving  | Energy saving timer                                      | minutes |
| Screen Timeout | Screen timeout delay                                     | minutes |
| Backup Reserve | Minimum battery % reserved for outages (Transfer Switch) | %       |

### Text

| Entity             | Description                                         | Format         |
|--------------------|-----------------------------------------------------|----------------|
| Charging Plan Time | Charging plan time window for supported devices     | `HH:mm-HH:mm`  |

## Services

The integration registers Home Assistant services for managing Transfer Switch charge/discharge plans. These services do not apply to portable device charging plans. They can be called from automations, scripts, or the Developer Tools.

| Service | Description |
|---------|-------------|
| `jackery.create_plan` | Create a new Transfer Switch charge or discharge plan |
| `jackery.update_plan` | Update an existing Transfer Switch plan |
| `jackery.delete_plan` | Delete a Transfer Switch plan by its ID |

### `jackery.create_plan`

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `type` | Yes | `1` = Charge, `2` = Discharge | `2` |
| `start_time` | Yes | Start time (`HH:MM`) | `"14:00"` |
| `end_time` | Yes | End time (`HH:MM`) | `"19:00"` |
| `days` | Yes | 7-char day mask Mon–Sun | `"1111100"` (weekdays) |
| `enabled` | No | Start enabled (default: `true`) | `true` |

### `jackery.update_plan`

| Field | Required | Description |
|-------|----------|-------------|
| `plan_id` | Yes | The plan ID (`pid`) to update |
| `type` | No | `1` = Charge, `2` = Discharge |
| `start_time` | No | Start time (`HH:MM`) |
| `end_time` | No | End time (`HH:MM`) |
| `days` | No | 7-char day mask Mon–Sun |
| `enabled` | No | Enable or disable the plan |

### `jackery.delete_plan`

| Field | Required | Description |
|-------|----------|-------------|
| `plan_id` | Yes | The plan ID (`pid`) to delete |

## Lovelace Cards

The card repository is separated for independent installation:

**[jackery-lovelace-cards](https://github.com/turmacar/jackery-lovelace-cards)**

All cards attempt to auto-discover entities and accept an optional `entity` config override.

### Transfer Switch Plan Management Card
- View all charge/discharge plans with day schedules
- Create new plans with type, time window, and day selection
- Toggle individual plans on/off
- Toggle individual days on/off per plan
- Delete plans
- Drag-to-reorder plan display
- Create divider labels
- Lock mode to prevent accidental changes

### Circuit Panel Card
- Two-bank layout (Bank A / Bank B) matching physical breaker panel
- Combined split-phase (240V) circuits displayed as double-height breakers
- Real-time power monitoring with color-coded levels and progress bars
- Lock/unlock circuit controls (default: locked)- Responsive: stacks banks vertically in narrow columns

### Schedule Heatmap Card
- Half-hour grid colored by plan type
- Overlapping plans shown with striped pattern
- Current time marker
- Schedule overlays (e.g. peak/off-peak) from HA schedule helpers
- Populates schedules by season via an `input_select` entity

## Device-Specific Availability

- Entities are created only when the Jackery API reports the underlying key for that device.
- Scheduled Plan entities (plan sensor and per-plan toggle switches) appear only for the Smart Transfer Switch.
- Fault diagnostic entities are created when the device reports an `fz` sub-object. Multi-state faults show human-readable labels; binary faults show Problem/OK.
- AC1/AC2 battery slot sensors appear when the Transfer Switch reports `ac1`/`ac2` sub-objects. Battery pack count sensors include per-pack serial number and battery level attributes. Add-on packs take time (~24h+) to populate after being plugged in.
- Circuit entities (power sensors and on/off switches) appear for Transfer Switch devices. Split-phase pairs are automatically combined into single entities.
- `Charging Plan` appears when the device reports DP `107`.
- `Charging Plan Time` and `Charging Plan Repeat` appear when the device reports DP `108`.
- Devices that split DC control into `odcu` and `odcc` will not show the combined `DC Output` entity.
- `Charging Plan Time` and `Charging Plan Repeat` become unavailable if the reported DP `108` payload is missing or malformed.
- Individual device `Charging Plan` entities are not available for devices connected to a Smart Transfer Switch.

## Installation

### Option 1: HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS
3. Search for "Jackery" in the integrations section
4. Click "Download" and restart Home Assistant

HACS installs published version tags from GitHub releases. This repository now publishes a matching GitHub release automatically whenever a semantic version tag is pushed.

If you need fixes that have not been published as a new GitHub release yet, HACS can also install the repository's default branch. This keeps branch installs available even while the latest published release remains `1.1.1`.

### Option 2: Manual Installation

1. Download or clone this repository
2. Copy the `jackery` folder to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Jackery" and select it
4. Enter your Jackery account credentials:
   - **Username**: Your Jackery account email/username
   - **Password**: Your Jackery account password
5. Click **Submit**

The integration will automatically discover your Jackery devices and create the supported entities for each one.

## Usage

Once configured, you'll find your Jackery devices and their entities in:

- **Settings** → **Devices & Services** → **Entities**
- Each device will have its own set of supported entities

You can use these entities in:

- **Dashboards**: Create custom dashboards to monitor your power station
- **Automations**: Set up automations based on battery level, power status, alarms, or control states
- **Templates**: Use sensor values in templates for custom calculations
- **Controls**: Change supported Jackery settings directly from Home Assistant

### Example Automations

```yaml
# Low battery alert
automation:
  - alias: "Low Battery Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.jackery_device_remaining_battery
      below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Jackery battery is low: {{ states('sensor.jackery_device_remaining_battery') }}%"

  # AC output turned on notification
  - alias: "Jackery AC Output On"
    trigger:
      platform: state
      entity_id: binary_sensor.jackery_device_ac_output
      to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Jackery AC output has been turned on"
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify your Jackery account credentials
   - Ensure your account is active and not locked

2. **No Devices Found**
   - Make sure your Jackery device is connected to the internet
   - Verify the device is registered to your account

3. **Sensors Not Updating**
   - Check the Home Assistant logs for errors
   - Verify your device has internet connectivity

### Logs

To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.jackery: debug
```

## Requirements

- Home Assistant 2023.8.0 or newer
- Python 3.10 or newer

## Dependencies

- `requests>=2.31.0`
- `pycryptodomex>=3.19.0`
- `socketry>=0.2.4`

## Contributing

Pull Requests are encouraged and welcome! For major changes, please open an issue first to discuss what you would like to change.

When changing `custom_components/jackery/manifest.json` version metadata, push the matching semantic version tag so HACS can install that version directly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based heavily on code from https://qiita.com/Hsky16/items/c163137265a87186ac39
- Thanks to the Home Assistant community for the excellent framework
- Special thanks to all contributors and users who provide feedback

---

**Note**: This is a community-driven integration and is not officially affiliated with Jackery. Use at your own risk.
