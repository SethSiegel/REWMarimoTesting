import json
# import asyncio
# from websockets.asyncio.client import connect
from websockets.sync.client import connect


class Lea_Settings():

    def mute(self):
        mute_dictionary = {"leaApi": "1.0",
                           "url": "amp/channels/1/output",
                           "method": "set",
                           "params": {"mute": True},
                           "id": 1}
        message = json.dumps(mute_dictionary)
        return message

    def unmute(self):
        unmute_dictionary = {"leaApi": "1.0",
                             "url": "amp/channels/1/output",
                             "method": "set",
                             "params": {"mute": False},
                             "id": 1}
        message = json.dumps(unmute_dictionary)
        return message

    def amp_deviceInfo(self):
        amp_deviceInfo_dictionary = {"leaApi": "1.0",
                                     "url": "amp/deviceInfo",
                                     "method": "get",
                                     "id": 1}
        message = json.dumps(amp_deviceInfo_dictionary)
        return message

    def channel_levels_get(self, channel: int = 1):
        """Get level-related data for a channel."""
        message_dictionary = {"leaApi": "1.0",
                              "url": f"amp/channels/{int(channel)}/levels",
                              "method": "get",
                              "id": 1}
        message = json.dumps(message_dictionary)
        return message

    def channel_output_get(self, channel: int = 1):
        """Get output-related data for a channel."""
        message_dictionary = {"leaApi": "1.0",
                              "url": f"amp/channels/{int(channel)}/output",
                              "method": "get",
                              "id": 1}
        message = json.dumps(message_dictionary)
        return message

    def build_set_command(self, url: str, params: dict, request_id: int = 1):
        """Build a LEA set command payload."""
        return {
            "leaApi": "1.0",
            "url": url,
            "method": "set",
            "params": params,
            "id": request_id,
        }

    def send_command(self, Lea_address: str, payload, timeout_seconds: float = 2.0):
        """Send a raw command payload (dict or JSON string)."""
        if isinstance(payload, dict):
            message = json.dumps(payload)
        else:
            message = payload
        return self.websocket_connect(
            Lea_address,
            message,
            timeout_seconds=timeout_seconds,
        )

    def send_batch(self, Lea_address: str, payloads, timeout_seconds: float = 2.0):
        """Send a list of payloads and return responses."""
        responses = []
        if payloads is None:
            return responses
        for payload in payloads:
            try:
                response = self.send_command(
                    Lea_address,
                    payload,
                    timeout_seconds=timeout_seconds,
                )
                responses.append({"payload": payload, "response": response, "error": None})
            except Exception as exc:
                responses.append({"payload": payload, "response": None, "error": str(exc)})
        return responses

    def return_amp_name(self, Lea_address: str):
        amp_name_string = self.websocket_connect(Lea_address,
                                                 self.amp_deviceInfo())
        amp_name_dict = json.loads(amp_name_string)
        amp_name = amp_name_dict['result']['deviceName']
        return amp_name

    def get_rms_limiter_value(
        self,
        Lea_address: str,
        channel: int = 1,
        timeout_seconds: float = 2.0,
    ):
        """Read RMS limiter value from LEA channel levels."""
        response_string = self.websocket_connect(
            Lea_address,
            self.channel_levels_get(channel),
            timeout_seconds=timeout_seconds,
        )
        response_dict = json.loads(response_string)
        result = response_dict.get("result", {})

        # Allow common LEA payload variants without breaking callers.
        if "rmsLimiter" in result:
            return result.get("rmsLimiter")
        if "totalRmsGainReduction" in result:
            return result.get("totalRmsGainReduction")
        limiter_block = result.get("limiter", {})
        if isinstance(limiter_block, dict) and "rms" in limiter_block:
            return limiter_block.get("rms")
        return None

    def get_measured_output_voltage(
        self,
        Lea_address: str,
        channel: int = 1,
        timeout_seconds: float = 2.0,
    ):
        """Read measured output voltage from LEA channel levels/output."""
        response_string = self.websocket_connect(
            Lea_address,
            self.channel_levels_get(channel),
            timeout_seconds=timeout_seconds,
        )
        response_dict = json.loads(response_string)
        result = response_dict.get("result", {})

        if "level_volts" in result:
            return result.get("level_volts")
        if "levelVolts" in result:
            return result.get("levelVolts")

        response_string = self.websocket_connect(
            Lea_address,
            self.channel_output_get(channel),
            timeout_seconds=timeout_seconds,
        )
        response_dict = json.loads(response_string)
        result = response_dict.get("result", {})

        # Allow common LEA payload variants without breaking callers.
        if "voltage" in result:
            return result.get("voltage")
        if "measuredVoltage" in result:
            return result.get("measuredVoltage")
        meter_block = result.get("meter", {})
        if isinstance(meter_block, dict):
            if "voltage" in meter_block:
                return meter_block.get("voltage")
            if "measuredVoltage" in meter_block:
                return meter_block.get("measuredVoltage")
        return None

    def crossover(self):
        ''' Function to set the crossover to a certain frequency

        '''
        dictionary = {"leaApi": "1.0",
                      "url": "amp/channels/1/levels",
                      "method": "set",
                      "params": {"fader": -20},
                      "id": 1}
        message = json.dumps(dictionary)
        return message

    def set_channel_gain(self, channel: int, gain_db: float, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/levels",
            {"fader": float(gain_db)},
            request_id=request_id,
        )

    def set_channel_delay(self, channel: int, delay_ms: float, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/output",
            {"delayMs": float(delay_ms)},
            request_id=request_id,
        )

    def set_channel_polarity(self, channel: int, polarity: str, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/output",
            {"polarity": str(polarity)},
            request_id=request_id,
        )

    def set_channel_peq(self, channel: int, bands, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/peq",
            {"bands": bands},
            request_id=request_id,
        )

    def set_channel_crossover(self, channel: int, config, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/crossover",
            {"config": config},
            request_id=request_id,
        )

    def set_channel_limiter(self, channel: int, config, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/limiters",
            {"config": config},
            request_id=request_id,
        )

    def set_channel_routing(self, channel: int, config, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/routing",
            {"config": config},
            request_id=request_id,
        )

    def set_channel_mute(self, channel: int, mute: bool, request_id: int = 1):
        return self.build_set_command(
            f"amp/channels/{int(channel)}/output",
            {"mute": bool(mute)},
            request_id=request_id,
        )

    def volume(self):
        ''' Function to set the volume to -20 dB

        Args:
            None

        Returns:
            None

        Notes:
            not sure this works, needs to be tested.
            fader might be the wrong string input

        '''
        dictionary = {"leaApi": "1.0",
                      "url": "amp/channels/1/levels",
                      "method": "set",
                      "params": {"fader": -20},
                      "id": 1}
        message = json.dumps(dictionary)
        return message

    def websocket_connect(self, address, message, timeout_seconds: float = 2.0):
        with connect(address, open_timeout=float(timeout_seconds)) as websocket:
            websocket.send(message)
            return_message = websocket.recv()
            print(return_message)
            websocket.close()
        return return_message


if __name__ == "__main__":
    current_script_path = __file__
    print(f'wrong file: {current_script_path}')
    print("This file is not meant to be run directly.")
    print("Please run the main script instead.")
