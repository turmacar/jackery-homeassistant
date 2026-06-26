"""The Jackery integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import JackeryAPI, JackeryAuthenticationError
from .const import DOMAIN, POLLING_INTERVAL_SEC

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TEXT,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Jackery integration."""
    # For config flow based integrations, this function should return True
    # to allow the integration to be discovered and configured via the UI
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jackery from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = JackeryAPI(
        account=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        device_list_response = await hass.async_add_executor_job(api.get_device_list)
        devices = device_list_response.get("data", [])
    except JackeryAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            f"Authentication failed while fetching Jackery devices: {err}"
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch Jackery devices: {err}") from err

    if not devices:
        _LOGGER.warning("No Jackery devices found for this account.")

    coordinators = {}
    for device in devices:
        device_id = device["devId"]
        device_name = device.get("devName", f"Jackery Device {device_id}")
        device_sn = device.get("devSn", "")
        is_transfer_switch = device.get("modelCode") == 2001

        # Persistent plan cache — survives across coordinator update cycles.
        # Populated by MQTT query on a throttled schedule; injected into every
        # coordinator update so plan entities always have data.
        plan_cache: dict[str, list[dict]] = {"plans": []}
        circuit_cache: dict[str, list[dict]] = {"circuits": []}
        plan_poll_counter = [0]
        circuit_poll_counter = [0]
        PLAN_QUERY_EVERY_N = 5  # query plans every Nth poll (~5 min at 60s)
        CIRCUIT_QUERY_EVERY_N = 3  # query circuits every Nth poll (~3 min)

        async def _async_update_data(
            api_client=api,
            dev_id=device_id,
            dev_sn=device_sn,
            is_box=is_transfer_switch,
            _counter=plan_poll_counter,
            _cir_counter=circuit_poll_counter,
            _plan_cache=plan_cache,
            _circuit_cache=circuit_cache,
        ):
            """Fetch data from API endpoint."""
            try:
                data = await asyncio.wait_for(
                    hass.async_add_executor_job(api_client.get_device_detail, dev_id),
                    timeout=10,
                )
                properties = dict(data.get("data", {}).get("properties", {}))
                if is_box:
                    _counter[0] += 1
                    if _counter[0] >= PLAN_QUERY_EVERY_N:
                        _counter[0] = 0
                        try:
                            plans = await api_client.async_query_transfer_switch_plans(dev_sn)
                            # Only update cache if we got actual plan data
                            if plans:
                                _plan_cache["plans"] = plans
                        except Exception:
                            _LOGGER.debug(
                                "Plan query failed for %s, keeping cached data",
                                dev_sn,
                            )
                    # Always inject cached plans into properties
                    properties["_plans"] = _plan_cache["plans"]

                    _cir_counter[0] += 1
                    if _cir_counter[0] >= CIRCUIT_QUERY_EVERY_N:
                        _cir_counter[0] = 0
                        try:
                            circuits = await api_client.async_query_transfer_switch_circuits(dev_sn)
                            if circuits:
                                _circuit_cache["circuits"] = circuits
                        except Exception:
                            _LOGGER.debug(
                                "Circuit query failed for %s, keeping cached data",
                                dev_sn,
                            )
                    # Always inject cached circuits into properties
                    properties["_circuits"] = _circuit_cache["circuits"]
                # Flatten nested fault dict so sensors can access
                # individual fault fields as top-level keys (fz_gs, fz_ol, etc.)
                fz = properties.get("fz")
                if isinstance(fz, dict):
                    for fk, fv in fz.items():
                        properties[f"fz_{fk}"] = fv

                properties["last_updated"] = dt_util.now()
                return properties
            except JackeryAuthenticationError as err:
                raise ConfigEntryAuthFailed(
                    f"Authentication failed while refreshing Jackery device {dev_id}: {err}"
                ) from err
            except Exception as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

        # Pre-seed plan and circuit caches before first coordinator refresh
        # so entities are created on the initial setup pass.
        if is_transfer_switch and device_sn:
            try:
                plans = await api.async_query_transfer_switch_plans(device_sn)
                if plans:
                    plan_cache["plans"] = plans
                    _LOGGER.debug("Pre-loaded %d plans for %s", len(plans), device_sn)
                else:
                    _LOGGER.debug("Initial plan query returned empty for %s", device_sn)
            except Exception:
                _LOGGER.debug("Initial plan query failed for %s, will retry", device_sn)
            try:
                circuits = await api.async_query_transfer_switch_circuits(device_sn)
                if circuits:
                    circuit_cache["circuits"] = circuits
                    _LOGGER.debug("Pre-loaded %d circuits for %s", len(circuits), device_sn)
                else:
                    _LOGGER.debug("Initial circuit query returned empty for %s", device_sn)
            except Exception:
                _LOGGER.debug("Initial circuit query failed for %s, will retry", device_sn)

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Jackery {device_name}",
            update_method=_async_update_data,
            update_interval=timedelta(seconds=POLLING_INTERVAL_SEC),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[device_id] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
        "devices": devices,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = hass.data.get(DOMAIN)
    entry_data = domain_data.get(entry.entry_id) if domain_data is not None else None
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry_data is not None:
            await entry_data["api"].async_close()
        if domain_data is not None:
            domain_data.pop(entry.entry_id, None)

    return unload_ok
