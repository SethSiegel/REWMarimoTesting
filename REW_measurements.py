
import time


class Measurements():
    def __init__(self, rew, dataH, Lea):
        self.rew = rew
        self.dataH = dataH
        self.Lea = Lea

    def sine_sweep(self, unitInput):
        """This function is used to take a sine sweep measurement

        Args:
            unitNumber (int): the unit number being tested
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """

        self.rew.post_measure_naming(f'{unitInput}')
        # this is where the SPL measurement is run
        self.rew.post_measure_command()

        return

    def stepped_sine_sweep(self, unitInput):
        """This function contains the code to setup and run a stepped sine
        sweep measurement. The returned data is the distortion data from
        the measurement.

        The data is returned in a dictionary format with the following keys:
        'distortion', 'frequency', 'harmonic', 'measurement', 'unitNumber',
        'unitType', 'uuid'

        The function does not return all the data from the measurement, only
        the distortion data.

        Args:
            unitNumber (int): the unit number being tested
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """
        # TODO: dummy line for now will figure out how to name the test later
        # TODO: currently not changing tot he right name and causing issues
        # self.rew.post_measure_naming(f'{unitInput}')
        unitInput = str(unitInput)
        self.rew.post_stepped_measurement_FFT_configuration()
        self.rew.post_stepped_measurement_frequency_span()
        self.rew.post_stepped_measurement_options()
        self.rew.post_stepped_measurement_type()
        # this is where the stepped sine measurement is run
        self.rew.post_stepped_measurement()
        progress = self.rew.get_stepped_sine_progress()
        print("Stepped sine sweep in progress... please wait")
        # the progress point will need to be variable and changable
        # currently checking to see if progress is equal to the last
        # update and if so we know the sweep is complete
        print(progress)
        while progress != {'point': 0, 'points': 14,
                           'message': '14 measurements required',
                           'timeRemainingSeconds': 0}:
            progress = self.rew.get_stepped_sine_progress()
            print(progress)
        print("Stepped sine sweep complete")
        steppedData = self.rew.get_measurements_distortion('1')
        return steppedData

    def save_measurements_mdat(self, unitInput):
        # TODO: check that this actually works and test it, idt it works
        """This function is used to save all measurements in REW to a mdat file

        Args:
            unitInput (str): the name of the unit being tested

        Returns:
            N/A
        """
        dummy_mdat_save = False
        dummy_mdat_output = ""
        while dummy_mdat_save is False:
            try:
                saveInput = input("Save all measurements? y/n: ")
                if saveInput == "y" or saveInput == "Y":
                    self.rew.post_measurements_command_saveall(unitInput)
                    dummy_mdat_output = "Measurements saved"
                    dummy_mdat_save = True
                elif saveInput == "n" or saveInput == "N":
                    dummy_mdat_output = "Measurements not saved"
                    dummy_mdat_save = True
            except ValueError:
                dummy_mdat_output = "Invalid input"
        return dummy_mdat_output

    def save_measurements_json(self, unitInput):
        # TODO: write this function
        """This function is used to save all measurements in REW to a json file
        i.e. it makes a big json full of all the measuremnt jsons
        that are on REW at the time this is run

        Args:
            unitNumber (int): the unit number being tested
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """
        # put code here
        pass

    def shutdown_REW(self):
        """This function is used to shut down REW

        Args:
            N/A

        Returns:
            N/A
        """
        dummy_shutdown = False
        shutdown_output = ""
        while dummy_shutdown is False:
            try:
                shutdownInput = input("Shutdown REW? y/n: ")
                if shutdownInput == "y" or shutdownInput == "Y":
                    self.rew.post_command_shutdown()
                    shutdown_output = "REW shutdown"
                    dummy_shutdown = True
                elif shutdownInput == "n" or shutdownInput == "N":
                    shutdown_output = "REW left running"
                    dummy_shutdown = True
            except ValueError:
                shutdown_output = "Invalid input"
        return shutdown_output

    def calculations_sine(self, measurements, num_of_mics, unitNumber):
        """This function is used to call dataHandling functions
        on the measurements for the sine tests

        Args:
            unitNumber (int): the unit number being tested
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """
        for i in range(0, num_of_mics, 1):
            # res_field is a list of the measurements available
            res_field = list(measurements.keys())[(-num_of_mics)+i]
            # response is the freq response for the ith measurement
            response = self.rew.get_measurements_id_freq_response(res_field)
            # processes the reponse data into a usable format
            decoded_array = self.dataH.decode_array(response["magnitude"])
            # loads in the SPL data from the benchmark file
            print(len(decoded_array))
            bench_array = self.dataH.load_json_column("SPL(dB)",
                                                      self.dataH.get_bmark(i+1))
            print(len(bench_array))
            # loads in the frequency data from the benchmark file
            freq_array = self.dataH.load_json_column("Freq(Hz)",
                                                     self.dataH.get_bmark(i+1))
            # calculates the difference between the measurment
            # and the benchmark data
            diff_list = self.dataH.list_dev_calc(bench_array, decoded_array)
            # checks if the unit passed or failed the test
            unit_PF = self.dataH.unit_pass_fail(diff_list)
            # creates a json file for the measurement data
            measurementLength = (len(measurements)-num_of_mics+1+i)
            self.dataH.make_json(measurements[str(measurementLength)]["title"],
                                 freq_array, decoded_array, measurements,
                                 str(len(measurements)-num_of_mics+1+i))

            if i == num_of_mics-1:
                mic_type = "acoustic"
                # dataH.plot_data(bench_array, decoded_array,
                # dataH.get_bmark(i+1))
                if unit_PF is True:
                    print(f"Unit passed {mic_type} P/F")
                else:
                    print(f"Unit failed {mic_type} P/F")
            else:
                mic_type = "vibration"
                # dataH.plot_data(bench_array, decoded_array,
                # dataH.get_bmark(i+1))
                if unit_PF is True:
                    print(f"Unit passed {mic_type} P/F")
                else:
                    print(f"Unit failed {mic_type} P/F")

        unitNumber = unitNumber + 1

        return unitNumber

    def calculations_stepped_sine(self, measurements, num_of_mics, unitNumber):
        """This function is used to call dataHandling functions
        on the measurements for the stepped sine tests
        Args:
            unitNumber (int): the unit number being tested
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """
        for i in range(0, num_of_mics, 1):
            # res_field is a list of the measurements available
            res_field = list(measurements.keys())[(-num_of_mics)+i]
            # response is the freq response for the ith measurement
            distortion = self.rew.get_measurements_distortion(res_field)["data"]
            distortion_array = []
            for j in range(0, len(distortion), 1):
                distortion_array.extend(distortion[j])
            # load in the data from the benchmark for distortion
            print(len(distortion))
            bench_data = self.dataH.load_json_column("data",
                                                     self.dataH.get_bmark(i+3))
            print(len(bench_data))
            # calculates the difference between the distortion data
            # and the benchmark data
            diff_list = self.dataH.list_dev_calc(bench_data, distortion_array)
            # checks if the unit passed or failed the test
            unit_PF = self.dataH.stepped_sine_pass_fail(diff_list)
            # creates a json file for the measurement data
            self.dataH.make_stepped_json(measurements[str(len(
                            measurements)-num_of_mics+1+i)]["title"],
                            distortion_array, measurements,
                            str(len(measurements)-num_of_mics+1+i))

            if i == num_of_mics-1:
                mic_type = "acoustic"
                # dataH.plot_data(bench_array, decoded_array,
                # dataH.get_bmark(i+1))
                if unit_PF is True:
                    print(f"Unit passed {mic_type} P/F")
                else:
                    print(f"Unit failed {mic_type} P/F")
            else:
                mic_type = "vibration"
                # dataH.plot_data(bench_array, decoded_array,
                # dataH.get_bmark(i+1))
                if unit_PF is True:
                    print(f"Unit passed {mic_type} P/F")
                else:
                    print(f"Unit failed {mic_type} P/F")
        unitNumber = unitNumber + 1

        return unitNumber

    def unit_selection(self):
        """This function is used to select the unit type

        Args:
            unitType (str): the type of unit being tested

        Returns:
            N/A
        """
        dummy_unit_selection = False
        while dummy_unit_selection is False:
            try:
                unitType = str(input("What kind of unit is being tested?:\n\
                    ResonX     (r/R):\n\
                    Bass Shaker(b/B):\n\
                    Exciter    (e/E):\n\
                    Thruster   (t/T): "))
                if unitType != "r" and unitType != "R" and unitType != "b"\
                    and unitType != "B" and unitType != "e" and\
                        unitType != "E" and unitType != "t" and\
                        unitType != "T":
                    raise ValueError("Invalid unit type")
                else:
                    dummy_unit_selection = True
            except ValueError:
                print("Invalid unit type")
        return unitType

    def unitInput(self, unitType, unitNumber):
        """This function is used to create the unit input name

        Args:
            unitType (str): the type of unit being tested
            unitNumber (int): the unit number being tested

        Returns:
            unitInput (str): the combination of the unit type and number
        """
        unitInput = str(unitType) + " " + str(unitNumber)
        return unitInput

    def REW_IO_Calibration(
        self,
        Lea_address: str,
        channel: int = 2,
        frequency_hz: float = 1000.0,
        target_voltage_v: float = 3.0,
        tone_seconds: float = 3.0,
        lea_timeout_seconds: float = 2.0,
        sample_delay_seconds: float = 1.5,
    ):
        """Run REW I/O calibration tone and capture LEA readings.

        Workflow:
        1. Configure REW generator for a sine tone at frequency_hz and
           target_voltage_v.
        2. Start tone output.
        3. Wait a short settle delay while tone is active.
        4. Read LEA RMS limiter value and measured output voltage.
        5. Keep tone running for remaining time, then stop output.

        Returns:
            dict: calibration result payload.
        """
        lea_rms_limiter_value = None
        lea_measured_voltage_v = None
        rew_calibrated_generator_voltage_v = None
        rew_calibration_apply_response = None
        lea_read_error = None
        rew_start_response = None
        rew_stop_response = None
        rew_start_error = None
        rew_stop_error = None
        debug_log = []

        try:
            debug_log.append("Starting REW generator tone (1000 Hz, 3.0 V).")
            rew_start_response = self.rew.start_generator_tone(
                frequency_hz=frequency_hz,
                level_volts=target_voltage_v,
            )
            debug_log.append(f"REW start response: {rew_start_response}")
            if isinstance(rew_start_response, dict):
                start_status_code = rew_start_response.get("_status_code")
                if isinstance(start_status_code, int) and start_status_code >= 400:
                    rew_start_error = (
                        f"HTTP {start_status_code} during generator start: "
                        f"{rew_start_response.get('_raw_text', '')}"
                    )
                    debug_log.append(f"REW start error detected: {rew_start_error}")
                start_message = str(rew_start_response.get("message", "")).lower()
                if "not a recognised command" in start_message or "failed" in start_message:
                    rew_start_error = rew_start_response.get("message")
                    debug_log.append(f"REW start command error: {rew_start_error}")
            _tone_total = max(0.0, float(tone_seconds))
            _sample_delay = max(0.0, min(float(sample_delay_seconds), _tone_total))
            if _sample_delay > 0:
                time.sleep(_sample_delay)
            debug_log.append(
                f"Sampling LEA during tone at t={_sample_delay:.2f}s "
                f"(total tone { _tone_total:.2f}s)."
            )
            try:
                debug_log.append("Reading LEA RMS limiter.")
                lea_rms_limiter_value = self.Lea.get_rms_limiter_value(
                    Lea_address=Lea_address,
                    channel=channel,
                    timeout_seconds=lea_timeout_seconds,
                )
                debug_log.append(f"LEA RMS limiter value: {lea_rms_limiter_value}")
                debug_log.append("Reading LEA measured output voltage.")
                lea_measured_voltage_v = self.Lea.get_measured_output_voltage(
                    Lea_address=Lea_address,
                    channel=channel,
                    timeout_seconds=lea_timeout_seconds,
                )
                debug_log.append(f"LEA measured output voltage: {lea_measured_voltage_v}")
            except Exception as lea_exc:
                lea_read_error = str(lea_exc)
                debug_log.append(f"LEA read error: {lea_read_error}")
            _remaining_tone = max(0.0, _tone_total - _sample_delay)
            if _remaining_tone > 0:
                time.sleep(_remaining_tone)
            debug_log.append("Tone duration complete.")
        except Exception as rew_start_exc:
            rew_start_error = str(rew_start_exc)
            debug_log.append(f"REW start exception: {rew_start_error}")
        finally:
            # Always attempt to stop generator even if reads fail.
            try:
                debug_log.append("Stopping REW generator tone.")
                rew_stop_response = self.rew.stop_generator_tone()
                debug_log.append(f"REW stop response: {rew_stop_response}")
                if isinstance(rew_stop_response, dict):
                    stop_status_code = rew_stop_response.get("_status_code")
                    if isinstance(stop_status_code, int) and stop_status_code >= 400:
                        rew_stop_error = (
                            f"HTTP {stop_status_code} during generator stop: "
                            f"{rew_stop_response.get('_raw_text', '')}"
                        )
                        debug_log.append(f"REW stop error detected: {rew_stop_error}")
                    stop_message = str(rew_stop_response.get("message", "")).lower()
                    if "not a recognised command" in stop_message or "failed" in stop_message:
                        rew_stop_error = rew_stop_response.get("message")
                        debug_log.append(f"REW stop command error: {rew_stop_error}")
            except Exception as rew_stop_exc:
                rew_stop_error = str(rew_stop_exc)
                debug_log.append(f"REW stop exception: {rew_stop_error}")

        voltage_match = False
        measured_voltage_float = None
        if isinstance(lea_measured_voltage_v, (int, float)):
            measured_voltage_float = float(lea_measured_voltage_v)
            voltage_match = abs(measured_voltage_float - float(target_voltage_v)) < 1e-6

        calibrate_level_value_raw = None
        if measured_voltage_float is not None and measured_voltage_float > 0:
            calibrate_level_value_raw = measured_voltage_float

        calibration_required = (
            measured_voltage_float is not None
            and measured_voltage_float > 0
            and not voltage_match
        )

        calibration_applied = False
        if calibration_required:
            rew_calibrated_generator_voltage_v = (
                float(target_voltage_v) * float(target_voltage_v)
            ) / measured_voltage_float
            rew_calibration_apply_response = self.rew.post_generator_configuration(
                frequency_hz=frequency_hz,
                level_volts=rew_calibrated_generator_voltage_v,
                signal="Sine",
            )
            calibration_applied = True
            debug_log.append(
                "Calibration applied from LEA level_volts. "
                f"New REW generator voltage: {rew_calibrated_generator_voltage_v}"
            )

        status = "ok"
        note = "Calibration succeeded."
        if lea_read_error is not None:
            status = "lea_read_failed"
            note = f"LEA read failed: {lea_read_error}"
        elif measured_voltage_float is None or measured_voltage_float == 0:
            status = "lea_read_failed"
            note = "LEA measured output voltage was zero or unavailable."
        elif calibration_applied:
            note = (
                "Calibration applied using LEA measured voltage. "
                f"REW generator voltage set to {rew_calibrated_generator_voltage_v} V."
            )
        elif voltage_match:
            note = "LEA measured output matches REW generator target."

        return {
            "status": status,
            "note": note,
            "generator_frequency_hz": float(frequency_hz),
            "rew_target_voltage_v": float(target_voltage_v),
            "tone_duration_seconds": float(tone_seconds),
            "lea_timeout_seconds": float(lea_timeout_seconds),
            "sample_delay_seconds": float(sample_delay_seconds),
            "lea_channel": int(channel),
            "rew_start_response": rew_start_response,
            "rew_stop_response": rew_stop_response,
            "rew_start_error": rew_start_error,
            "rew_stop_error": rew_stop_error,
            "lea_read_error": lea_read_error,
            "debug_log": debug_log,
            "lea_rms_limiter_value": lea_rms_limiter_value,
            "lea_measured_output_voltage_v": lea_measured_voltage_v,
            "voltage_match": voltage_match,
            "calibration_required": calibration_required,
            "rew_calibrate_level_value_raw": calibrate_level_value_raw,
            "rew_calibrated_generator_voltage_v": rew_calibrated_generator_voltage_v,
            "rew_calibration_apply_response": rew_calibration_apply_response,
        }


if __name__ == "__main__":
    current_script_path = __file__
    print(f'wrong file: {current_script_path}')
    print("This file is not meant to be run directly.")
    print("Please run the main script instead.")
