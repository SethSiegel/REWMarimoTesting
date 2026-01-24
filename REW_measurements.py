
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


if __name__ == "__main__":
    current_script_path = __file__
    print(f'wrong file: {current_script_path}')
    print("This file is not meant to be run directly.")
    print("Please run the main script instead.")
