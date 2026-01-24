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

    def return_amp_name(self, Lea_address: str):
        amp_name_string = self.websocket_connect(Lea_address,
                                                 self.amp_deviceInfo())
        amp_name_dict = json.loads(amp_name_string)
        amp_name = amp_name_dict['result']['deviceName']
        return amp_name

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

    def websocket_connect(self, address, message):
        with connect(address) as websocket:
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
