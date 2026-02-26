import requests
import time
import subprocess
import sys
import os
from urllib.parse import urlencode
from pathlib import Path
from project_paths import get_mdat_dir, ensure_data_dirs


class REWAutomation():
    def __init__(self,
                 rew_address: str = "http://localhost",
                 port: int = 4735,
                 rew_filepath: str = ""):
        """ Initializes the REW software and API

        Establishes a connection to the REW executable in either windows or
        macOS environments
        and sets up the API at the default local port 4735.

        Args:
            rew_address (str): the rew address
            port (int): the default port REW hosts on
            rew_filepath (str): an empty string for now, but will be used
                                to specify the filepath of REW

        Returns:
            N/A

        """
        self.rew_address = rew_address
        if rew_filepath == "":
            if sys.platform == "win32":
                # use default REW filepath for Windows
                self.rew_filepath = 'C:\\Program Files\\REW\\roomeqwizard.exe'
            elif sys.platform == "darwin":
                self.rew_filepath = '/Applications/REW/REW.app'
            else:
                raise OSError("REWAutomation couldn't find REW on this \
                              platform, please specify the rew_filepath \
                              argument in the constructor")

        else:
            self.rew_filepath = rew_filepath
        self.port = port
        self.is_server_up = False
        self._existing_rew_running = False
        self._launched_rew = False

        # Prefer attaching to an already-running REW API instance.
        if self._api_is_up(self.port):
            self.is_server_up = True
            return

        # On macOS, if REW is already open, do not relaunch. Try to attach.
        if sys.platform == "darwin" and self._is_rew_process_running():
            self._existing_rew_running = True
            _detected_port = self._detect_running_api_port()
            if _detected_port is not None:
                self.port = _detected_port
                self.is_server_up = True
            return

        if sys.platform == "win32":
            subprocess.Popen([self.rew_filepath,
                              '-api',
                              # '-nogui',
                              '-port',
                              str(self.port)
                              ])
            self._launched_rew = True
        elif sys.platform == "darwin":
            subprocess.Popen(['open',
                              '-a',
                              self.rew_filepath,
                              '--args',
                              '-api',
                              # '-nogui',
                              '-port',
                              str(self.port)
                              ])
            self._launched_rew = True

    def get_application_commands(self):
        """ Function to get all application commands

        Args:
            None

        Returns:
            application commands (dict): all application commands
        """
        get_response = self.get_request("/application/commands")
        return get_response

    def is_server_setup(self, retries: int = 30, sleep_seconds: float = 1.0):
        """ Function to check if REW is ready to accept requests

        Args:
            None

        Returns:
            is_server_up (bool): True if REW is ready, False if not
        """
        if self.is_server_up:
            return True

        for _ in range(int(retries)):
            if self._api_is_up(self.port):
                print("REW is ready")
                self.is_server_up = True
                return True
            print("REW is not ready. Retrying in 1 second.")
            time.sleep(float(sleep_seconds))

        if self._existing_rew_running:
            print(
                f"REW is running but API was not detected on port {self.port}. "
                "Use an API-enabled REW instance or launch REW from this interface."
            )
        return False

    def get_request(self, request_ext: str):
        """ Function to make a GET request to the REW API

        Args:
            request_ext (str): the extension of the request to be made

        Returns:
            response (dict): the response from the request

        """
        response = requests.get(self.rew_address +
                                ":" + str(self.port) + request_ext)
        return self._parse_api_response(response)

    def load_mdat(self, filepath: str):
        """ Function to load a .mdat file into REW

        Args:
            filepath (str): the filepath of the measurement file to be loaded

        Returns:
            N/A
        """
        body_to_load = {
            "command": "Load",
            "parameters": [
                filepath
            ]
        }

        post_response = self.post_request("/measurements/command",
                                          body_to_load)
        return post_response

    def save_mdat(self, filepath: str):
        """ Function to save all measurements in REW to a .mdat file

        Args:
            filepath (str): the filepath where the .mdat file will be saved

        Returns:
            N/A
        """

        body_to_save = {
            "command": "Save all",
            "parameters": [
                filepath
            ]
        }
        post_response = self.post_request("/measurements/command",
                                          body_to_save)
        return post_response

    def get_measurements(self):
        """ Function to get all measurements

        Args:
            None

        Returns:
            measurements (dict): all measurements
        """
        get_response = self.get_request("/measurements")
        return get_response

    def get_measurements_id(self, id: str):
        """ Function to get a measurement by its id#

        Args:
            id (str): the id of the measurement to be retrieved

        Returns:
            measurement (dict): the measurement with the specified id
        """
        get_response = self.get_request("/measurements/" + id)
        return get_response

    def get_measurements_id_freq_response(self, id: str, smoothing=None,
                                          unit=None, ppo=None):
        """ Function to get the frequency response of a specified measurement

        Args:
            id (str): the id of the measurement whose frequency response it
                        to be retrieved
            smoothing (str | None): smoothing option, e.g. "1/12"
            unit (str | None): unit for magnitude, e.g. "SPL"
            ppo (int | None): points-per-octave for log spacing

        Returns:
            measurement (dict): the frequency response of the
                                specified measurement
        """
        get_request_body = "/measurements/" + id + "/frequency-response"
        query_parts = []
        if smoothing:
            smoothing_value = str(smoothing)
            if not (smoothing_value.startswith('"') and smoothing_value.endswith('"')):
                smoothing_value = f"\"{smoothing_value}\""
            query_parts.append(f"smoothing={smoothing_value}")
        if unit:
            query_parts.append(f"unit={unit}")
        if ppo:
            query_parts.append(f"ppo={ppo}")
        if query_parts:
            get_request_body = get_request_body + "?" + "&".join(query_parts)
        get_response = self.get_request(get_request_body)
        return get_response

    def get_measurements_frequency_response_smoothing_choices(self):
        """ Function to get smoothing choices for frequency responses """
        get_response = self.get_request(
            "/measurements/frequency-response/smoothing-choices"
        )
        return get_response

    def get_measurements_distortion(self, id: str):
        """ Function to get the distortion of the measurements

        Args:
            None

        Returns:
            measurements (dict): the distortion of the measurements
        """
        get_response = self.get_request(f"/measurements/{id}/distortion")
        return get_response

    def get_stepped_sine_progress(self):
        """ Function to get the progress of the stepped sine sweep

        Args:
            None

        Returns:
            progress (dict): the progress of the stepped sine sweep
        """
        get_request_body = "/stepped-measurement/progress"
        get_response = self.get_request(get_request_body)
        return get_response

    def get_last_input(self):
        """ Function to get the last input used in REW

        Args:
            None

        Returns:
            last_input (dict): the last input used in REW
        """
        get_request_body = "/audio/asio/last-input"
        get_response = self.get_request(get_request_body)
        return get_response

    def post_request(self, request_ext: str, data: dict):
        """ Function to make a POST request to REW API

        Args:
            request_ext (str): the extension of the request to be made
            data (dict): the data to be sent in the request

        Returns:
            N/A
        """
        response = requests.post(self.rew_address + ':'
                                 + str(self.port) + request_ext, json=data)
        return self._parse_api_response(response)

    def _parse_api_response(self, response):
        """Parse REW API response without failing on empty/non-JSON bodies."""
        try:
            return response.json()
        except ValueError:
            return {
                "_json_parse_error": True,
                "_status_code": response.status_code,
                "_reason": response.reason,
                "_raw_text": response.text,
                "_content_type": response.headers.get("content-type", ""),
            }

    def _api_is_up(self, port: int) -> bool:
        try:
            response = requests.get(
                f"{self.rew_address}:{port}/application/commands",
                timeout=1.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    def _detect_running_api_port(self):
        candidate_ports = [self.port] + list(range(4735, 4741))
        for candidate_port in candidate_ports:
            if self._api_is_up(candidate_port):
                return candidate_port
        return None

    def _is_rew_process_running(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            # pgrep exit code 0 means at least one REW process is running.
            return subprocess.call(
                ["pgrep", "-f", "REW.app"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) == 0
        except Exception:
            return False

    def post_measure_sweep_config(self, sweep_configuration: dict = {}):
        """HTTP POSTs measure sweep configuration to REW

        If there is no sweep configuration passed in, the default sweep
        configuration will be used.

        Args:
            sweep_configuration (dict): Dictionary of sweep configuration.
                Defaults to None.

        Returns:
            response (dict): Dictionary of response from REW

        """

        if sweep_configuration == {}:
            sweep_configuration = {
                "startFrequency": 0,
                "stopFrequency": 20000,
                "length": "256k",
                "fillSilenceWithDither": False
            }

        response = self.post_request("/measure/sweep/configuration",
                                     sweep_configuration)
        return response

    def post_measure_naming(self, name: str = "test", testNumber: int = 1):
        """ Function to chang the measurement name field

        Args:
            name (str): the name of the measurement
            testNumber (int): the number of the measurement

        Returns:
            N/A
        """
        post_response = self.post_request("/measure/naming",
                                          {"title": name,
                                           'nextNumber': testNumber,
                                           'numberIncrement': 1})
        return post_response

    def post_measure_command(self, command: str = "SPL"):
        """ Function to take a measurement

        Args:
            command (str): default measurement taken is SPL

        Returns:
            N/A
        """
        measurement_to_take = {
            "command": command
        }
        post_response = self.post_request("/measure/command",
                                          measurement_to_take)
        return post_response

    def post_audio_driver(self, driver: str = "ASIO"):
        """ Function to change the audio driver

            Args:
                driver (str): the default audio driver is ASIO

            Returns:
                N/A

        """
        post_response = self.post_request("/audio/driver", {"driver": driver})
        return post_response

    def post_audio_device(self, device: str = "Dante Virtual Soundcard (x64)"):
        """ Function to change the audio device
        Args:
            device (str): the default audio device is Dante Virtual Soundcard

        Returns:
            N/A
        """
        command = {"device": device}
        post_response = self.post_request("/audio/asio/device", command)
        return post_response

    def post_audio_asio_input(self, input: str = "2: Dante rx 2"):
        """ Function to set the number of audio inputs to be used

        Args:
            input (str): the key field for the input change
            input_name (str): the name of the last input to be used

        Returns:
            N/A
        """
        command = {"input": input}
        post_response = self.post_request("/audio/asio/input", command)
        return post_response

    def post_audio_asio_output(self, output: str = "2: Dante rx 2"):
        """ Function to set the number of audio inputs to be used

        Args:
            output (str): the key field for the ouput change

        Returns:
            N/A
        """
        command = {"output": output}
        post_response = self.post_request("/audio/asio/output", command)
        return post_response

    def post_no_overall_average(self, no_overall_average: bool = True):
        """ Function to turn off the overall average setting in REW

        Args:
            no_overall_average (bool): True to turn off the overall average,
                                       False to turn it on

        Returns:
            N/A
        """
        command = no_overall_average
        api_endpoint = "/measure/no-overall-average"
        post_response = self.post_request(api_endpoint, command)
        return post_response

    def post_measurements_command_saveall(self, filename: str = "test"):
        """ Function to save all measurements in REW to a .mdat file

        Args:
            filename (str): the name of the .mdat file to be saved

        Returns:
            N/A
        """

        ensure_data_dirs()
        filepath = str(get_mdat_dir() / f"{filename}.mdat")
        message = '''These are the saved files from automation prototyping'''
        body = {"command": "Save all",
                "parameters": [filepath,
                               message
                               ]
                }
        post_response = self.post_request("/measurements/command", body)
        return post_response

    def post_command_shutdown(self):
        """ Function to shutdown REW

        Args:
            None

        Returns:
            N/A
        """
        post_response = self.post_request("/application/command",
                                          {"command": "Shutdown"})
        return post_response

    def post_stepped_measurement(self):
        setTime = "settlingTimems"
        post_response = self.post_request("/stepped-measurement/command",
                                          {"command": "start",
                                           "parameters": {setTime: "0",
                                                          "leveldBFS": "-20"}})
        return post_response

    def post_stepped_measurement_FFT_configuration(self):
        fftc = "fft-configuration"
        post_response = self.post_request(f"/stepped-measurement/{fftc}",
                                          {
                                            "fftLength": "16k",
                                            "averages": 2,
                                            "maximumOverlap": "0%",
                                            "window": "Hann"
                                            })
        return post_response

    def post_stepped_measurement_frequency_span(self):
        freSpan = "frequency-span"
        post_response = self.post_request(f"/stepped-measurement/{freSpan}",
                                          {
                                            "startFreq": 50.0,
                                            "endFreq": 1000.0,
                                            "ppo": 3
                                           })
        return post_response

    def post_stepped_measurement_options(self):
        distortionLimit = "reduceStepIfDistortionLimitHit"
        post_response = self.post_request("/stepped-measurement/options",
                                          {
                                            "silenceIntervalSeconds": 0,
                                            "captureSpectrum": "true",
                                            "stopForHeavyClipping": "false",
                                            "stopAtDistortionLimit": "false",
                                            "distortionLimitPercent": 1.0,
                                            distortionLimit: "false"
                                            })
        return post_response

    def post_stepped_measurement_type(self):
        post_response = self.post_request("/stepped-measurement/type",
                                          "THD vs frequency")
        return post_response

    def post_generator_configuration(
        self,
        frequency_hz: float = 1000.0,
        level_volts: float = 3.0,
        signal: str = "Sine",
    ):
        """Configure REW's signal generator.

        Args:
            frequency_hz (float): Generator tone frequency in Hz.
            level_volts (float): Generator level in volts.
            signal (str): Generator signal type (default "Sine").

        Returns:
            dict: REW API response.
        """
        payload = {
            "signal": signal,
            "frequency": float(frequency_hz),
            "level": float(level_volts),
            "levelUnit": "V",
        }
        return self.post_request("/generator/configuration", payload)

    def post_generator_command(self, command: str = "Play"):
        """Send a command to REW's generator endpoint.

        Args:
            command (str): Generator command such as "Play" or "Stop".

        Returns:
            dict: REW API response.
        """
        return self.post_request("/generator/command", {"command": command})

    def start_generator_tone(self, frequency_hz: float = 1000.0,
                             level_volts: float = 3.0):
        """Configure and start generator tone output."""
        self.post_generator_configuration(
            frequency_hz=frequency_hz,
            level_volts=level_volts,
            signal="Sine",
        )
        return self.post_generator_command("Play")

    def stop_generator_tone(self):
        """Stop generator tone output."""
        return self.post_generator_command("Stop")


if __name__ == "__main__":
    current_script_path = __file__
    print(f'wrong file: {current_script_path}')
    print("This file is not meant to be run directly.")
    print("Please run the main script instead.")
