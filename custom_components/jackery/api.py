"""API client for Jackery cloud services."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import inspect
import json
import logging
import threading
import time
import uuid
from typing import Optional

import requests
from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad

try:
    import aiomqtt
except ModuleNotFoundError:
    aiomqtt = None

try:
    import socketry
    from socketry.client import _mqtt_params as _socketry_mqtt_params
except ModuleNotFoundError as err:  # pragma: no cover - dependency provided in prod
    if err.name == "socketry":
        socketry = None
        _socketry_mqtt_params = None
    else:
        raise

_LOGGER = logging.getLogger(__name__)


class JackeryAuthenticationError(Exception):
    """Exception to indicate an authentication error."""


class JackeryAPI:
    """A client to interact with the Jackery Cloud API."""

    def __init__(
        self, account: str, password: str, android_id: str = "abcd1234567890ef"
    ):
        """Initialize the API client."""
        self.account = account
        self.password = password
        self.android_id = android_id
        self.base_url = "https://iot.jackeryapp.com"
        self._token: Optional[str] = None
        self._token_expiry_time: float = (
            0  # We will assume a long expiry for simplicity
        )
        self._mqtt_user_id: Optional[str] = None
        self._mqtt_password_b64: Optional[str] = None
        self._mac_id: str = self._generate_udid()
        self._control_client = None
        self._control_client_lock = asyncio.Lock()
        self._control_write_lock = asyncio.Lock()
        self._login_lock = threading.Lock()
        self._last_login_time: float = 0
        # TEMP (race investigation): tracks concurrently-open MQTT connections
        # across socketry and raw aiomqtt paths. Remove once resolved.
        self._mqtt_race_active: dict[str, float] = {}

    def _name_uuid_from_bytes_java(self, data: bytes) -> str:
        """Generate a version 3 UUID using an MD5 hash."""
        md5_digest = hashlib.md5(data).digest()
        u = uuid.UUID(bytes=md5_digest, version=3)
        return str(u).replace("-", "")

    def _generate_udid(self) -> str:
        """Generate a UDID."""
        if self.android_id and self.android_id != "9774d56d682e549c":
            return "2" + self._name_uuid_from_bytes_java(
                self.android_id.encode("utf-8")
            )
        else:
            random_uuid_str = str(uuid.uuid4()).replace("-", "")
            return "9" + random_uuid_str

    def _encrypt_with_aes(self, plain_text: str, aes_key: bytes) -> str:
        """Perform AES encryption."""
        cipher = AES.new(aes_key, AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(plain_text.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted).decode("utf-8")

    def _encrypt_with_rsa(self, data: bytes, public_key_b64: str) -> str:
        """Perform RSA encryption."""
        pub_key_pem = (
            f"-----BEGIN PUBLIC KEY-----\n{public_key_b64}\n-----END PUBLIC KEY-----"
        )
        pub_key = RSA.importKey(pub_key_pem)
        cipher = PKCS1_v1_5.new(pub_key)
        encrypted = cipher.encrypt(data)
        return base64.b64encode(encrypted).decode("utf-8")

    def login(self) -> bool:
        """Perform the login process and store the token."""
        with self._login_lock:
            # If another thread just logged in, reuse its credentials
            if time.monotonic() - self._last_login_time < 5 and self._token:
                _LOGGER.debug("Skipping login — another thread refreshed credentials %.1fs ago",
                              time.monotonic() - self._last_login_time)
                return True
            return self._login_inner()

    def _login_inner(self) -> bool:
        """Actual login implementation (must be called with _login_lock held)."""
        _LOGGER.info("Attempting to login to Jackery service")
        mac_id = self._generate_udid()
        login_bean = {
            "account": self.account,
            "loginType": 2,
            "macId": mac_id,
            "password": self.password,
            "phone": "",
            "registerAppId": "com.hbxn.jackery",
            "verificationCode": "",
        }

        public_key_b64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCVmzgJy/4XolxPnkfu32YtJqYGFLYqf9/rnVgURJED+8J9J3Pccd6+9L97/+7COZE5OkejsgOkqeLNC9C3r5mhpE4zk/HStss7Q8/5DqkGD1annQ+eoICo3oi0dITZ0Qll56Dowb8lXi6WHViVDdih/oeUwVJY89uJNtTWrz7t7QIDAQAB"
        aes_key = b"1234567890123456"
        login_bean_json = json.dumps(login_bean, ensure_ascii=False)
        aes_encrypt_data = self._encrypt_with_aes(login_bean_json, aes_key)
        rsa_for_aes_key = self._encrypt_with_rsa(aes_key, public_key_b64)

        url = f"{self.base_url}/v1/auth/login"
        params = {"aesEncryptData": aes_encrypt_data, "rsaForAesKey": rsa_for_aes_key}
        headers = {
            "app_version": "1.0.5",
            "upload-incomplete": "?0",
            "sys_version": "17.2",
            "platform": "1",
            "upload-draft-interop-version": "3",
            "accept": "*/*",
            "accept-language": "en-US",
            "accept-encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "User-Agent": "DxPowerProject/1.0.5 (com.hb.jackery; build:2; iOS 17.2.0) Alamofire/5.8.0",
            "model": "iPad Pro (12.9-inch) (3rd generation)",
        }
        files = {"file": ("", b"", "")}

        try:
            response = requests.post(
                url, params=params, headers=headers, files=files, timeout=10
            )
            _LOGGER.debug("Login response status: %s", response.status_code)
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("Login response data: %s", data)

            if data.get("code") == 0 and "token" in data:
                self._token = data["token"]
                login_data = data.get("data", {})
                self._mqtt_user_id = str(login_data.get("userId", ""))
                self._mqtt_password_b64 = str(login_data.get("mqttPassWord", ""))
                self._last_login_time = time.monotonic()
                # Invalidate cached socketry client so next control use rebuilds
                # with fresh credentials rather than a stale token.
                self._control_client = None
                _LOGGER.info("Successfully logged in and obtained token.")
                return True
            else:
                error_msg = f"Login failed: {data.get('msg', 'Unknown error')} (code: {data.get('code')})"
                _LOGGER.error(error_msg)
                raise JackeryAuthenticationError(data.get("msg", "Login failed"))
        except requests.RequestException as e:
            _LOGGER.error("Login request failed: %s", e)
            raise JackeryAuthenticationError(f"Request failed: {e}") from e

    def _get_request(self, url_path: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to the API, handling token expiry."""
        if not self._token:
            _LOGGER.info("No token found, logging in.")
            if not self.login():
                raise JackeryAuthenticationError("Unable to login to retrieve token.")

        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "app_version": "1.0.5",
            "sys_version": "17.2",
            "accept-encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "accept-language": "en-US",
            "platform": "1",
            "user-agent": "DxPowerProject/1.0.5 (com.hb.jackery; build:2; iOS 17.2.0) Alamofire/5.8.0",
            "model": "iPad Pro (12.9-inch) (3rd generation)",
            "token": self._token,
        }
        full_url = f"{self.base_url}{url_path}"
        _LOGGER.debug("Making API request to: %s", full_url)

        try:
            response = requests.get(
                full_url, headers=headers, params=params, timeout=10
            )
            _LOGGER.debug("API response status: %s", response.status_code)
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("API response data: %s", data)

            # 10402 = token expired; 10403 = session displaced by another login
            if data.get("code") in (10402, 10403):
                _LOGGER.info("Re-logging in (code=%s)...", data.get("code"))
                if not self.login():
                    raise JackeryAuthenticationError(
                        "Failed to re-login after session invalidated."
                    )
                # Retry the request with the new token
                headers["token"] = self._token
                response = requests.get(
                    full_url, headers=headers, params=params, timeout=10
                )
                response.raise_for_status()
                data = response.json()

            if data.get("code") != 0:
                error_msg = f"API Error: {data.get('msg', 'Unknown error')} (code: {data.get('code')})"
                _LOGGER.error(error_msg)
                raise Exception(error_msg)

            return data

        except requests.RequestException as e:
            _LOGGER.error("API request failed: %s", e)
            raise

    def get_device_list(self) -> dict:
        """Get the list of devices."""
        _LOGGER.info("Attempting to fetch device list from Jackery API")
        try:
            result = self._get_request("/v1/device/bind/list")
            _LOGGER.info("Successfully retrieved device list")
            return result
        except Exception as e:
            _LOGGER.error("Failed to get device list: %s", str(e))
            raise

    def get_device_detail(self, device_id: str) -> dict:
        """Get detailed information for a specified device."""
        return self._get_request("/v1/device/property", params={"deviceId": device_id})

    async def _async_get_control_client(self):
        """Get an authenticated Socketry client for device control."""
        async with self._control_client_lock:
            if self._control_client is not None:
                return self._control_client

            if socketry is None:
                raise RuntimeError("socketry is not installed")
            if not self._mqtt_user_id or not self._mqtt_password_b64 or not self._token:
                raise RuntimeError("MQTT credentials not available — call login() first")

            # Build from existing HA credentials to avoid a new HTTP login that
            # would rotate the auth token. Omitting email/password prevents
            # socketry from ever calling _http_login internally.
            creds = {
                "userId": self._mqtt_user_id,
                "mqttPassWord": self._mqtt_password_b64,
                "token": self._token,
                "macId": self._mac_id,
                "deviceSn": "",
                "deviceId": "",
                "deviceName": "",
                "devices": [],
            }
            client = None
            label = "socketry:init"
            self._mqtt_race_start(label)
            try:
                client = socketry.Client(creds)
                await client.fetch_devices()
            except asyncio.CancelledError:
                await self._async_close_control_client(client)
                raise
            except Exception:
                await self._async_close_control_client(client)
                raise
            finally:
                self._mqtt_race_end(label)
            self._control_client = client
            # TEMP: mark socketry client as persistently connected so aiomqtt opens show as races
            self._mqtt_race_active["socketry:client"] = time.monotonic()
            _LOGGER.debug("MQTT-RACE-CHECK: socketry client now connected")
            return client

    async def async_close(self) -> None:
        """Release any cached Socketry control client."""
        async with self._control_write_lock:
            await self._async_reset_control_client()

    async def _async_reset_control_client(self, client=None) -> None:
        """Drop the cached control client and close the discarded instance."""
        async with self._control_client_lock:
            client_to_close = self._control_client if client is None else client
            if client is None:
                self._control_client = None
                # TEMP: socketry client gone — clear persistent-connection marker
                if self._mqtt_race_active.pop("socketry:client", None) is not None:
                    _LOGGER.debug("MQTT-RACE-CHECK: socketry client disconnected")
            elif self._control_client is client:
                self._control_client = None

        await self._async_close_control_client(client_to_close)

    async def _async_close_control_client(self, client) -> None:
        """Best-effort close a discarded Socketry control client."""
        if client is None:
            return

        for method_name in ("stop", "disconnect", "close"):
            method = getattr(client, method_name, None)
            if method is None:
                continue

            try:
                result = method()
                if inspect.isawaitable(result):
                    await result
            except asyncio.CancelledError:
                raise
            except Exception as err:  # pragma: no cover - defensive cleanup
                _LOGGER.debug(
                    "Failed to %s discarded Socketry control client: %s",
                    method_name,
                    err,
                )

    def _mqtt_race_start(self, label: str) -> None:
        """TEMP (race investigation): record a connection attempt starting."""
        now = time.monotonic()
        others = {k: round(now - t, 2) for k, t in self._mqtt_race_active.items()}
        self._mqtt_race_active[label] = now
        if others:
            _LOGGER.debug(
                "MQTT-RACE-CHECK: opening %s while already open: %s",
                label, others,
            )
        else:
            _LOGGER.debug("MQTT-RACE-CHECK: opening %s (no concurrent connections)", label)

    def _mqtt_race_end(self, label: str) -> None:
        """TEMP (race investigation): record a connection attempt ending."""
        start = self._mqtt_race_active.pop(label, None)
        if start is not None:
            _LOGGER.debug(
                "MQTT-RACE-CHECK: closed %s after %.2fs", label, time.monotonic() - start,
            )

    async def async_set_device_property(
        self,
        device_id: str,
        device_sn: str,
        property_slug: str,
        value: str | int,
    ) -> None:
        """Set a device property through Jackery's MQTT control channel."""
        if socketry is None:
            raise RuntimeError("socketry is not installed")

        async with self._control_write_lock:
            client = await self._async_get_control_client()

            for attempt in range(2):
                try:
                    device = self._resolve_control_device(client, device_id, device_sn)
                    await device.set_property(property_slug, value, wait=True)
                    return
                except (
                    socketry.AuthenticationError,
                    socketry.MqttError,
                    socketry.SocketryError,
                    KeyError,
                ):
                    if attempt == 1:
                        await self._async_reset_control_client(client)
                        raise
                    await self._async_reset_control_client(client)
                    client = await self._async_get_control_client()

    def _build_mqtt_params(self) -> tuple[dict, str]:
        """Build aiomqtt connection params from REST API login credentials.

        Returns ``(params_dict, user_id)``.
        """
        if _socketry_mqtt_params is None:
            raise RuntimeError("socketry is not installed")
        if not self._mqtt_user_id or not self._mqtt_password_b64:
            raise RuntimeError("MQTT credentials not available — call login() first")
        creds = {
            "userId": self._mqtt_user_id,
            "mqttPassWord": self._mqtt_password_b64,
            "macId": self._mac_id,
        }
        return _socketry_mqtt_params(creds), self._mqtt_user_id

    async def async_send_transfer_switch_command(
        self,
        device_id: str,
        device_sn: str,
        action_id: int,
        body: dict,
        message_type: str = "DevicePropertyChange",
    ) -> None:
        """Send a raw MQTT command using the Transfer Switch protocol.

        Uses MQTT credentials from the REST API login to avoid a
        separate socketry login session that would compete for the
        single-session MQTT password.
        """
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")

        for attempt in range(2):
            params, user_id = self._build_mqtt_params()
            topic = f"hb/app/{user_id}/command"
            ts = int(time.time() * 1000)
            payload = json.dumps(
                {
                    "deviceSn": device_sn,
                    "id": ts,
                    "version": 0,
                    "messageType": message_type,
                    "actionId": action_id,
                    "timestamp": ts,
                    "body": body,
                },
                separators=(",", ":"),
            )
            _LOGGER.info(
                "MQTT publish: topic=%s actionId=%d body=%s",
                topic, action_id, body,
            )
            _LOGGER.info("MQTT payload: %s", payload)
            try:
                dev_topic = f"hb/app/{user_id}/device"
                label = f"aiomqtt:command:actionId={action_id}"
                self._mqtt_race_start(label)
                try:
                    async with aiomqtt.Client(**params) as mqtt:
                        await mqtt.subscribe(dev_topic, qos=1)
                        await mqtt.publish(topic, payload, qos=1)
                        # Wait briefly for device response
                        try:
                            async with asyncio.timeout(5):
                                async for message in mqtt.messages:
                                    try:
                                        data = json.loads(message.payload)
                                    except (json.JSONDecodeError, TypeError):
                                        continue
                                    _LOGGER.info(
                                        "MQTT response: messageType=%s actionId=%s body=%s",
                                        data.get("messageType"),
                                        data.get("actionId"),
                                        data.get("body"),
                                    )
                                    if data.get("deviceSn") == device_sn:
                                        return
                        except TimeoutError:
                            _LOGGER.warning(
                                "No MQTT response within 5s for actionId=%d",
                                action_id,
                            )
                finally:
                    self._mqtt_race_end(label)
                return
            except Exception:
                if attempt == 1:
                    raise
                _LOGGER.debug(
                    "Transfer switch command failed (attempt %d), "
                    "refreshing credentials and retrying",
                    attempt + 1,
                )
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.login)

    async def async_set_device_dp(
        self,
        device_id: str,
        device_sn: str,
        dp_id: str | int,
        value: str | int | bool,
    ) -> None:
        """Set a raw device DP through the existing control channel."""
        await self.async_set_device_property(
            device_id,
            device_sn,
            str(dp_id),
            value,
        )

    @staticmethod
    def _resolve_control_device(client, device_id: str, device_sn: str):
        """Resolve a controllable device from the cached Socketry device list."""
        for device in client.devices:
            if str(device.get("devId", "")) == str(device_id):
                return client.device(str(device["devSn"]))
            if device_sn and str(device.get("devSn", "")) == str(device_sn):
                return client.device(str(device["devSn"]))

        raise KeyError(
            f"Unable to resolve Jackery device for control (device_id={device_id}, "
            f"device_sn={device_sn})."
        )

    async def async_query_transfer_switch_plans(
        self,
        device_sn: str,
    ) -> list[dict]:
        """Query charge/discharge plans from Transfer Switch via MQTT.

        Opens a short-lived MQTT connection, sends a QueryElectricityStrategy
        command, and waits for the response containing the ``cds`` plan list.
        Socketry's subscribe loop filters out non-DevicePropertyChange messages,
        so this method handles the MQTT exchange directly.
        """
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")

        params, user_id = self._build_mqtt_params()

        cmd_topic = f"hb/app/{user_id}/command"
        dev_topic = f"hb/app/{user_id}/device"
        ts = int(time.time() * 1000)
        payload = json.dumps(
            {
                "deviceSn": device_sn,
                "id": ts,
                "version": 0,
                "messageType": "QueryElectricityStrategy",
                "actionId": 12,
                "timestamp": ts,
                "body": {"cmd": 15},
            },
            separators=(",", ":"),
        )

        try:
            label = "aiomqtt:query_plans"
            self._mqtt_race_start(label)
            try:
                async with aiomqtt.Client(**params) as mqtt:
                    await mqtt.subscribe(dev_topic, qos=1)
                    await mqtt.publish(cmd_topic, payload, qos=1)
                    try:
                        async with asyncio.timeout(10):
                            async for message in mqtt.messages:
                                try:
                                    data = json.loads(message.payload)
                                except (json.JSONDecodeError, TypeError):
                                    continue
                                if (
                                    data.get("deviceSn") == device_sn
                                    and isinstance(data.get("body"), dict)
                                    and "cds" in data["body"]
                                ):
                                    return data["body"]["cds"]
                    except TimeoutError:
                        _LOGGER.warning(
                            "Timeout waiting for plan query response from %s",
                            device_sn,
                        )
            finally:
                self._mqtt_race_end(label)
        except Exception:
            _LOGGER.exception("Failed to query plans for %s", device_sn)

        return []

    async def async_update_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        plan: dict,
    ) -> None:
        """Update an existing charge/discharge plan on the Transfer Switch."""
        await self.async_send_transfer_switch_command(
            device_id,
            device_sn,
            14,  # actionId for UpdateElectricityStrategy
            {"cmd": 17, **plan},
            message_type="UpdateElectricityStrategy",
        )

    async def async_create_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        plan: dict,
    ) -> None:
        """Create a new charge/discharge plan on the Transfer Switch."""
        await self.async_send_transfer_switch_command(
            device_id,
            device_sn,
            13,  # actionId for InsertElectricityStrategy
            {"cmd": 16, **plan},
            message_type="InsertElectricityStrategy",
        )

    async def async_delete_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        pid: str,
    ) -> None:
        """Delete a charge/discharge plan on the Transfer Switch."""
        await self.async_send_transfer_switch_command(
            device_id,
            device_sn,
            15,  # actionId for DeleteElectricityStrategy
            {"cmd": 18, "pid": pid},
            message_type="DeleteElectricityStrategy",
        )

    async def async_query_transfer_switch_circuits(
        self,
        device_sn: str,
    ) -> list[dict]:
        """Query circuit properties from Transfer Switch via MQTT.

        Opens a short-lived MQTT connection, sends a QueryCircuitProperty
        command, and waits for the response containing the ``cir`` list.
        """
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")

        params, user_id = self._build_mqtt_params()

        cmd_topic = f"hb/app/{user_id}/command"
        dev_topic = f"hb/app/{user_id}/device"
        ts = int(time.time() * 1000)
        payload = json.dumps(
            {
                "deviceSn": device_sn,
                "id": ts,
                "version": 0,
                "messageType": "QueryCircuitProperty",
                "actionId": 7,
                "timestamp": ts,
                "body": {"cmd": 10},
            },
            separators=(",", ":"),
        )

        try:
            label = "aiomqtt:query_circuits"
            self._mqtt_race_start(label)
            try:
                async with aiomqtt.Client(**params) as mqtt:
                    await mqtt.subscribe(dev_topic, qos=1)
                    await mqtt.publish(cmd_topic, payload, qos=1)
                    try:
                        async with asyncio.timeout(10):
                            async for message in mqtt.messages:
                                try:
                                    data = json.loads(message.payload)
                                except (json.JSONDecodeError, TypeError):
                                    continue
                                # actionId=7 is the QueryCircuitProperty response (full metadata).
                                # actionId=1 are unsolicited partial power-only pushes — ignore them.
                                if (
                                    data.get("deviceSn") == device_sn
                                    and data.get("actionId") == 7
                                    and isinstance(data.get("body"), dict)
                                    and "cir" in data["body"]
                                ):
                                    return data["body"]["cir"]
                                # TEMP: log filtered cir messages to confirm fix is working
                                if data.get("deviceSn") == device_sn and "cir" in (data.get("body") or {}):
                                    _LOGGER.debug(
                                        "MQTT-RACE-CHECK: ignoring cir message with actionId=%d from %s",
                                        data.get("actionId"), device_sn,
                                    )
                    except TimeoutError:
                        _LOGGER.warning(
                            "Timeout waiting for circuit query response from %s",
                            device_sn,
                        )
            finally:
                self._mqtt_race_end(label)
        except Exception:
            _LOGGER.exception("Failed to query circuits for %s", device_sn)

        return []

    async def async_set_circuit_switch(
        self,
        device_id: str,
        device_sn: str,
        idx: int,
        on: bool,
    ) -> None:
        """Toggle a circuit on/off on the Transfer Switch."""
        await self.async_send_transfer_switch_command(
            device_id,
            device_sn,
            9,  # actionId for circuit switch
            {"cmd": 12, "idx": idx, "sw": 1 if on else 0},
        )
