# Troubleshooting

## Debug Logging

To enable verbose logging for the integration, add the following to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.jackery: debug
```

Logs can be viewed under **Settings** > **System** > **Logs**.

## Common Issues

### Authentication Failed

- Verify your Jackery account credentials.
- Ensure the account is active and not locked.
- **EU accounts are not currently supported.** If your account was registered through the EU region, the integration will not be able to authenticate.

### No Devices Found

- Confirm your device is connected to the internet and powered on.
- Verify the device is registered to the same account used during integration setup.

### Sensors Not Updating

- Check the Home Assistant logs for errors related to `custom_components.jackery`.
- Verify the device has a stable internet connection.

### Plan or Circuit Entities Missing

- Plan and circuit entities are only created for the Smart Transfer Switch.
- Both are queried on startup via the persistent MQTT connection. If the initial query has not yet completed, entities may appear within a few minutes of setup.
- If entities are still missing after several minutes, check the logs for MQTT connection errors.

### AC1/AC2 Pack Sensors Not Appearing

Add-on battery pack sensors can take 24 hours or more to appear after a pack is first connected. The device registers the pack gradually over time.

### Charging Plan Time / Repeat Unavailable

These entities become unavailable if the device reports DP 108 with a missing or malformed payload, or when the device is connected to a Smart Transfer Switch. Check device connectivity and wait for the next successful poll.

---

For example automations, see [Example Automations](Example-Automations).
