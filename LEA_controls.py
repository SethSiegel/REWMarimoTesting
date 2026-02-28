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
