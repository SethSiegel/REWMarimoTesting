import asyncio
import websockets
import json
import time
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class LEAMonitor:

    def __init__(self, amp_address: str, output_dir: str = "logs"):
        self.amp_address = amp_address
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.connected = False
        self.monitoring = False
        self.current_frequency = 1000.0
        self.current_signal_type = "off"
        self.logging_start_time = None

        self.latest_data = {
            "levels": {},
            "impedance": {},
            "voltage": {},
            "current": {},
            "power": {},
            "status": {},
            "power_supply": {},
            "timestamp": None
        }

        self.channel_faders = {
            "output": {},
            "generator": {}
        }

        self.callbacks = []

        self.message_id = 1
        self.pending_responses = {}

        self.channel_count = 0
        self.detected_channels = set()

        self.receive_loop_running = False

        self.csv_path = None
        self.csv_file = None
        self.csv_writer = None

        self._new_data_since_last_log = False
        self._periodic_log_task: Optional[asyncio.Task] = None

        self.STALENESS_TIMEOUT = 2.0
        self._field_timestamps = {
            "voltage": {},
            "current": {},
            "power": {},
            "levels": {},
            "impedance": {},
            "status": {},
        }

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.amp_address)
            self.connected = True
            print(f"Connected to LEA amplifier at {self.amp_address}")

            await self.subscribe_to_channels()

            return True
        except Exception as e:
            print(f"Failed to connect to LEA: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        self.connected = False
        self.receive_loop_running = False

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"Error closing websocket: {e}")
            self.websocket = None
            print("Disconnected from LEA amplifier")

        if self.csv_file:
            self.csv_file.close()

    def build_message(self, url: str, method: str, params: Dict[str, Any] = None):
        message = {
            "leaApi": "1.0",
            "url": url,
            "method": method,
            "id": self.message_id
        }
        if params:
            message["params"] = params

        self.message_id += 1
        return json.dumps(message)

    async def send_message(self, url: str, method: str, params: Dict[str, Any] = None, wait_for_response: bool = False, timeout: float = 3.0):
        if not self.connected or not self.websocket:
            print("Not connected to LEA")
            return False

        message_dict = {
            "leaApi": "1.0",
            "url": url,
            "method": method,
            "id": self.message_id
        }
        if params:
            message_dict["params"] = params

        msg_id = self.message_id
        self.message_id += 1

        if wait_for_response:
            response_future = asyncio.Future()
            self.pending_responses[msg_id] = response_future

        message = json.dumps(message_dict)
        try:
            await self.websocket.send(message)

            if wait_for_response:
                try:
                    result = await asyncio.wait_for(response_future, timeout=timeout)
                    return result.get("success", True)
                except asyncio.TimeoutError:
                    print(f"Timeout waiting for response to message {msg_id}", flush=True)
                    if msg_id in self.pending_responses:
                        del self.pending_responses[msg_id]
                    return False
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            if wait_for_response and msg_id in self.pending_responses:
                del self.pending_responses[msg_id]
            return False

    async def subscribe_to_channels(self):
        for channel in range(1, 9):
            await self.send_message(f"/amp/channels/{channel}/levels", "subscribe")
            await asyncio.sleep(0.01)

            await self.send_message(f"/amp/channels/{channel}/loadMonitor", "subscribe")
            await asyncio.sleep(0.01)

        await self.send_message("/amp/channels", "get")

        await self.send_message("/amp/powerSupply", "subscribe")
        await asyncio.sleep(0.01)

        await self.send_message("/amp/powerSupply", "get")
        await asyncio.sleep(0.01)

    async def set_signal_generator(self, signal_type: str, frequency: float = None):
        params = {"type": signal_type}
        if frequency is not None:
            params["frequency"] = frequency

        self.current_signal_type = signal_type
        if frequency is not None:
            self.current_frequency = frequency

        result = await self.send_message("/amp/signalGenerator", "set", params, wait_for_response=True, timeout=5.0)
        return result

    async def enable_signal_generator(self, channel: int, enabled: bool, fader: float = 0.0):
        params = {
            "signalGeneratorEnable": enabled,
            "signalGeneratorFader": fader
        }
        self.channel_faders["generator"][str(channel)] = fader
        return await self.send_message(f"/amp/channels/{channel}/inputSelector", "set", params, wait_for_response=True, timeout=3.0)

    async def set_output_gain(self, channel: int, fader: float, mute: bool = False):
        params = {
            "fader": fader,
            "mute": mute
        }
        self.channel_faders["output"][str(channel)] = fader if not mute else -100.0
        return await self.send_message(f"/amp/channels/{channel}/output", "set", params, wait_for_response=True, timeout=3.0)

    async def get_device_info(self):
        return await self.send_message("/amp/deviceInfo", "get")

    def register_callback(self, callback):
        self.callbacks.append(callback)

    async def notify_callbacks(self, data_type: str, data: Any):
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_type, data)
                else:
                    callback(data_type, data)
            except Exception as e:
                print(f"Error in callback: {e}")

    async def receive_loop(self):
        if self.receive_loop_running:
            print("Receive loop already running, skipping")
            return

        self.receive_loop_running = True
        try:
            while self.connected and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )

                    data = json.loads(message)
                    await self.process_message(data)

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by LEA")
                    self.connected = False
                    break
                except Exception as e:
                    print(f"Error in receive loop: {e}")
                    break
        finally:
            self.receive_loop_running = False

    async def process_message(self, message: Dict[str, Any]):
        if "method" in message and message["method"] == "notify":
            params = message.get("params", {})

            if "amp" in params and "channels" in params["amp"]:
                channels = params["amp"]["channels"]

                for channel_num, channel_data in channels.items():
                    if "levels" in channel_data:
                        levels = channel_data["levels"]
                        self.latest_data["levels"][channel_num] = levels
                        now = time.time()
                        self._field_timestamps["levels"][channel_num] = now

                        if "level_db" in levels:
                            await self.notify_callbacks("level", {
                                "channel": channel_num,
                                "level_db": levels["level_db"],
                                "timestamp": now
                            })

                        if "level_volts" in levels or "level_amps" in levels:
                            voltage = levels.get("level_volts", 0)
                            current_val = levels.get("level_amps", 0)
                            power_watts = voltage * current_val

                            self.latest_data["voltage"][channel_num] = voltage
                            self.latest_data["current"][channel_num] = current_val
                            self.latest_data["power"][channel_num] = power_watts

                            if "level_volts" in levels:
                                self._field_timestamps["voltage"][channel_num] = now
                            if "level_amps" in levels:
                                self._field_timestamps["current"][channel_num] = now
                            self._field_timestamps["power"][channel_num] = now

                            await self.notify_callbacks("voltage", {
                                "channel": channel_num,
                                "voltage": voltage,
                                "timestamp": now
                            })

                            await self.notify_callbacks("current", {
                                "channel": channel_num,
                                "current": current_val,
                                "timestamp": now
                            })

                            await self.notify_callbacks("power", {
                                "channel": channel_num,
                                "power": power_watts,
                                "timestamp": now
                            })

                    if "loadMonitor" in channel_data:
                        load_monitor = channel_data["loadMonitor"]
                        self.latest_data["impedance"][channel_num] = load_monitor
                        now = time.time()

                        if "measuredImpedance" in load_monitor:
                            self._field_timestamps["impedance"][channel_num] = now
                            await self.notify_callbacks("impedance", {
                                "channel": channel_num,
                                "impedance": load_monitor["measuredImpedance"],
                                "timestamp": now
                            })

                    if "output" in channel_data:
                        output = channel_data["output"]
                        status_data = {
                            "ready": output.get("ready", False),
                            "fault": output.get("fault", False),
                            "clip": output.get("clip", False),
                            "thermal": output.get("thermal", False),
                            "limiting": output.get("limiting", False)
                        }
                        self.latest_data["status"][channel_num] = status_data
                        self._field_timestamps["status"][channel_num] = time.time()

                        await self.notify_callbacks("status", {
                            "channel": channel_num,
                            **status_data,
                            "timestamp": time.time()
                        })

                    if "inputSelector" in channel_data:
                        input_selector = channel_data["inputSelector"]
                        await self.notify_callbacks("channel_state_update", {
                            "channel": channel_num,
                            "signalGeneratorEnable": input_selector.get("signalGeneratorEnable", False),
                            "signalGeneratorFader": input_selector.get("signalGeneratorFader", 0.0),
                            "timestamp": time.time()
                        })

                self.latest_data["timestamp"] = time.time()
                self._new_data_since_last_log = True

            if "amp" in params and "powerSupply" in params["amp"]:
                ps_data = params["amp"]["powerSupply"]
                for key, value in ps_data.items():
                    self.latest_data["power_supply"][key] = value

                ps = self.latest_data["power_supply"]
                await self.notify_callbacks("power_supply", {
                    "ac_line_voltage": ps.get("acLineVoltage", 0),
                    "ac_line_current": ps.get("acLineCurrent", 0),
                    "ac_line_watts": ps.get("acLineWatts", 0),
                    "est_power_auto_standby": ps.get("estPowerUsageAutoStandby", "0"),
                    "est_power_poe": ps.get("estPowerUsagePoe", "0"),
                    "fault": ps.get("fault", False),
                    "thermal": ps.get("thermal", False),
                    "poe_status": ps.get("poeStatus", False),
                    "power_ok": ps.get("powerOk", False),
                    "power_source": ps.get("powerSource", ""),
                    "line_warning": ps.get("lineWarning", False),
                    "timestamp": time.time()
                })

        elif "url" in message and "result" in message:
            url = message["url"]
            result = message["result"]
            message_id = message.get("id", None)

            timestamp_str = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp_str}] LEA response for {url}: {result}", flush=True)

            if message_id is not None and message_id in self.pending_responses:
                future = self.pending_responses.pop(message_id)
                if not future.done():
                    future.set_result({"success": True, "result": result})

            if url == "/amp/deviceInfo":
                await self.notify_callbacks("device_info", result)
            elif url == "/amp/channels":
                if isinstance(result, dict):
                    channel_keys = [k for k in result.keys() if k.isdigit()]
                    if channel_keys:
                        self.channel_count = len(channel_keys)
                        self.detected_channels = set(int(k) for k in channel_keys)
                        await self.notify_callbacks("channel_count", {
                            "count": self.channel_count,
                            "channels": sorted(list(self.detected_channels))
                        })
                await self.notify_callbacks("channels_data", result)
            elif url == "/amp/signalGenerator":
                await self.notify_callbacks("signal_generator_response", {
                    "success": True,
                    "result": result,
                    "message_id": message_id
                })
            elif "/amp/channels/" in url and "/inputSelector" in url:
                channel = url.split("/")[3]
                await self.notify_callbacks("channel_enable_response", {
                    "success": True,
                    "channel": channel,
                    "result": result,
                    "message_id": message_id
                })
            elif "/amp/channels/" in url and "/output" in url:
                channel = url.split("/")[3]
                await self.notify_callbacks("output_gain_response", {
                    "success": True,
                    "channel": channel,
                    "result": result,
                    "message_id": message_id
                })
            elif url == "/amp/powerSupply":
                for key, value in result.items():
                    self.latest_data["power_supply"][key] = value

                ps = self.latest_data["power_supply"]
                await self.notify_callbacks("power_supply", {
                    "ac_line_voltage": ps.get("acLineVoltage", 0),
                    "ac_line_current": ps.get("acLineCurrent", 0),
                    "ac_line_watts": ps.get("acLineWatts", 0),
                    "est_power_auto_standby": ps.get("estPowerUsageAutoStandby", "0"),
                    "est_power_poe": ps.get("estPowerUsagePoe", "0"),
                    "fault": ps.get("fault", False),
                    "thermal": ps.get("thermal", False),
                    "poe_status": ps.get("poeStatus", False),
                    "power_ok": ps.get("powerOk", False),
                    "power_source": ps.get("powerSource", ""),
                    "line_warning": ps.get("lineWarning", False),
                    "timestamp": time.time()
                })

        elif "error" in message:
            error_info = message.get("error", {})
            url = message.get("url", "unknown")
            message_id = message.get("id", None)

            timestamp_str = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp_str}] LEA command error for {url}: {error_info}", flush=True)

            if message_id is not None and message_id in self.pending_responses:
                future = self.pending_responses.pop(message_id)
                if not future.done():
                    future.set_result({"success": False, "error": error_info})

            await self.notify_callbacks("command_error", {
                "success": False,
                "url": url,
                "error": error_info,
                "message_id": message_id
            })

    async def start_logging(self, filename=None):
        if filename:
            log_filename = filename
        else:
            log_filename = f"lea_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.csv_path = self.output_dir / log_filename
        self.csv_file = open(self.csv_path, 'w', newline='')
        fieldnames = [
            'timestamp', 'frequency', 'signal_type', 'data_source',
            'ps_acLineVoltage', 'ps_acLineCurrent', 'ps_acLineWatts', 'ps_powerSource',
            'ps_fault', 'ps_thermal', 'ps_poeStatus', 'ps_powerOk', 'ps_powerSwitchState',
            'ps_lineWarning', 'ps_lineWarningAutoLimits', 'ps_lineLowLimitWarning', 'ps_lineHighLimitWarning',
            'ps_estPowerUsageAutoStandby', 'ps_estPowerUsagePoe',
            'ps_outputPortMode', 'ps_outputPortPolarity', 'ps_inputPortPolarity',
            'ch1_output_fader', 'ch1_generator_fader', 'ch1_level_db', 'ch1_voltage', 'ch1_current', 'ch1_power', 'ch1_impedance', 'ch1_thermal', 'ch1_fault', 'ch1_clip', 'ch1_limiting',
            'ch2_output_fader', 'ch2_generator_fader', 'ch2_level_db', 'ch2_voltage', 'ch2_current', 'ch2_power', 'ch2_impedance', 'ch2_thermal', 'ch2_fault', 'ch2_clip', 'ch2_limiting',
            'ch3_output_fader', 'ch3_generator_fader', 'ch3_level_db', 'ch3_voltage', 'ch3_current', 'ch3_power', 'ch3_impedance', 'ch3_thermal', 'ch3_fault', 'ch3_clip', 'ch3_limiting',
            'ch4_output_fader', 'ch4_generator_fader', 'ch4_level_db', 'ch4_voltage', 'ch4_current', 'ch4_power', 'ch4_impedance', 'ch4_thermal', 'ch4_fault', 'ch4_clip', 'ch4_limiting',
            'ch5_output_fader', 'ch5_generator_fader', 'ch5_level_db', 'ch5_voltage', 'ch5_current', 'ch5_power', 'ch5_impedance', 'ch5_thermal', 'ch5_fault', 'ch5_clip', 'ch5_limiting',
            'ch6_output_fader', 'ch6_generator_fader', 'ch6_level_db', 'ch6_voltage', 'ch6_current', 'ch6_power', 'ch6_impedance', 'ch6_thermal', 'ch6_fault', 'ch6_clip', 'ch6_limiting',
            'ch7_output_fader', 'ch7_generator_fader', 'ch7_level_db', 'ch7_voltage', 'ch7_current', 'ch7_power', 'ch7_impedance', 'ch7_thermal', 'ch7_fault', 'ch7_clip', 'ch7_limiting',
            'ch8_output_fader', 'ch8_generator_fader', 'ch8_level_db', 'ch8_voltage', 'ch8_current', 'ch8_power', 'ch8_impedance', 'ch8_thermal', 'ch8_fault', 'ch8_clip', 'ch8_limiting',
        ]
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self._new_data_since_last_log = False
        self.monitoring = True
        self.logging_start_time = time.time() * 1000
        self._periodic_log_task = asyncio.create_task(self._periodic_log_loop())
        print(f"Started logging to {self.csv_path}")

    async def stop_logging(self):
        self.monitoring = False
        self.logging_start_time = None
        if self._periodic_log_task is not None:
            self._periodic_log_task.cancel()
            try:
                await self._periodic_log_task
            except asyncio.CancelledError:
                pass
            self._periodic_log_task = None
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
        print(f"Stopped logging")

    async def _periodic_log_loop(self):
        while self.monitoring:
            await asyncio.sleep(0.1)
            if self.monitoring:
                self.log_to_csv()

    def _is_stale(self, field_type, channel_str, now):
        last_update = self._field_timestamps.get(field_type, {}).get(channel_str)
        if last_update is None:
            return None
        return (now - last_update) > self.STALENESS_TIMEOUT

    def _stale_or_value(self, field_type, channel_str, value, now):
        staleness = self._is_stale(field_type, channel_str, now)
        if staleness is None:
            return ""
        if staleness:
            return 0
        return value

    def log_to_csv(self):
        if not self.csv_writer or not self.monitoring:
            return

        data_source = "live" if self._new_data_since_last_log else "fill"
        self._new_data_since_last_log = False

        now = time.time()
        timestamp_iso = datetime.now().isoformat(timespec='milliseconds')

        ps = self.latest_data.get("power_supply", {})

        def ps_val(key):
            val = ps.get(key)
            if val is None:
                return ""
            if isinstance(val, bool):
                return int(val)
            return val

        row = {
            'timestamp': timestamp_iso,
            'frequency': self.current_frequency,
            'signal_type': self.current_signal_type,
            'data_source': data_source,
            'ps_acLineVoltage': ps_val("acLineVoltage"),
            'ps_acLineCurrent': ps_val("acLineCurrent"),
            'ps_acLineWatts': ps_val("acLineWatts"),
            'ps_powerSource': ps_val("powerSource"),
            'ps_fault': ps_val("fault"),
            'ps_thermal': ps_val("thermal"),
            'ps_poeStatus': ps_val("poeStatus"),
            'ps_powerOk': ps_val("powerOk"),
            'ps_powerSwitchState': ps_val("powerSwitchState"),
            'ps_lineWarning': ps_val("lineWarning"),
            'ps_lineWarningAutoLimits': ps_val("lineWarningAutoLimits"),
            'ps_lineLowLimitWarning': ps_val("lineLowLimitWarning"),
            'ps_lineHighLimitWarning': ps_val("lineHighLimitWarning"),
            'ps_estPowerUsageAutoStandby': ps_val("estPowerUsageAutoStandby"),
            'ps_estPowerUsagePoe': ps_val("estPowerUsagePoe"),
            'ps_outputPortMode': ps_val("outputPortMode"),
            'ps_outputPortPolarity': ps_val("outputPortPolarity"),
            'ps_inputPortPolarity': ps_val("inputPortPolarity"),
        }

        for ch in range(1, 9):
            ch_str = str(ch)

            row[f'ch{ch}_output_fader'] = self.channel_faders["output"].get(ch_str, "")
            row[f'ch{ch}_generator_fader'] = self.channel_faders["generator"].get(ch_str, "")

            if ch_str in self.latest_data["levels"]:
                levels = self.latest_data["levels"][ch_str]
                raw_db = levels.get("level_db", "")
                row[f'ch{ch}_level_db'] = self._stale_or_value("levels", ch_str, raw_db, now)
            else:
                row[f'ch{ch}_level_db'] = ""

            raw_voltage = self.latest_data["voltage"].get(ch_str)
            raw_current = self.latest_data["current"].get(ch_str)
            raw_power = self.latest_data["power"].get(ch_str)

            row[f'ch{ch}_voltage'] = self._stale_or_value("voltage", ch_str, raw_voltage, now) if raw_voltage is not None else ""
            row[f'ch{ch}_current'] = self._stale_or_value("current", ch_str, raw_current, now) if raw_current is not None else ""
            row[f'ch{ch}_power'] = self._stale_or_value("power", ch_str, raw_power, now) if raw_power is not None else ""

            if ch_str in self.latest_data["impedance"]:
                impedance = self.latest_data["impedance"][ch_str]
                raw_imp = impedance.get("measuredImpedance")
                row[f'ch{ch}_impedance'] = self._stale_or_value("impedance", ch_str, raw_imp, now) if raw_imp is not None else ""
            else:
                row[f'ch{ch}_impedance'] = ""

            if ch_str in self.latest_data["status"]:
                staleness = self._is_stale("status", ch_str, now)
                if staleness is None or staleness:
                    row[f'ch{ch}_thermal'] = 0
                    row[f'ch{ch}_fault'] = 0
                    row[f'ch{ch}_clip'] = 0
                    row[f'ch{ch}_limiting'] = 0
                else:
                    status = self.latest_data["status"][ch_str]
                    row[f'ch{ch}_thermal'] = int(status.get("thermal", False))
                    row[f'ch{ch}_fault'] = int(status.get("fault", False))
                    row[f'ch{ch}_clip'] = int(status.get("clip", False))
                    row[f'ch{ch}_limiting'] = int(status.get("limiting", False))
            else:
                row[f'ch{ch}_thermal'] = ""
                row[f'ch{ch}_fault'] = ""
                row[f'ch{ch}_clip'] = ""
                row[f'ch{ch}_limiting'] = ""

        self.csv_writer.writerow(row)
        self.csv_file.flush()

    def get_latest_data(self):
        return self.latest_data.copy()
