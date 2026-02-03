import base64
import struct
import json
import jsonpickle
import os
import math
from project_paths import get_json_dir, get_stepped_sine_dir, ensure_data_dirs


class Data_Handling():
    def sanitize_filename(self, name, replacement="_"):
        """Return a filesystem-safe filename (no path separators or reserved chars)."""
        if name is None:
            return "untitled"
        safe = str(name).strip()
        if not safe:
            return "untitled"
        invalid = '<>:"/\\|?*'
        for ch in invalid:
            safe = safe.replace(ch, replacement)
        safe = safe.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        safe = safe.strip().strip(".")
        return safe if safe else "untitled"

    def decode_array(self, base64_encoded):
        """ Function to decode a base64 encoded array

        Args:
            base64_encoded (str): the base64 encoded array

        Returns:
            readable_array (list): the decoded array
        """
        decoded_array = base64.b64decode(base64_encoded)
        readable_array = self.byte_to_float_array(decoded_array)
        return readable_array

    def byte_to_float_array(self, bytes_data):
        """ Function to convert a byte array to a float array

        This little guy is big endian decoded

        Args:
            bytes_data (list): the byte array to be converted

        Returns:
            float_array (list): the converted float array
        """
        float_array = list(struct.unpack('>' + 'f' * (len(bytes_data) // 4),
                                         bytes_data))
        return float_array

    def build_freq_array_from_response(self, response, length):
        """Build frequency array for a REW FrequencyResponse.

        Uses startFreq with either freqStep (linear) or ppo (log spaced).
        The length should match the decoded magnitude array length.
        """
        if response is None or length is None or length <= 0:
            return []

        start_freq = response.get("startFreq")
        freq_step = response.get("freqStep")
        ppo = response.get("ppo")

        if start_freq is None:
            return []

        if freq_step is not None:
            return [start_freq + i * freq_step for i in range(length)]

        if ppo is not None:
            ratio = math.exp(math.log(2.0) / ppo)
            return [start_freq * (ratio ** i) for i in range(length)]

        return []

    # separate file
    def load_json_column(self, column: str = "SPL(dB)",
                         filepath: str = "benchmark"):
        """ Function to load the SPL data from a .json file

        Args:
            filepath (str): the filepath of the .json file

        Returns:
            float_array (list): the SPL data from the .json file
        """
        float_array = []
        with open(filepath) as f:
            data = json.load(f)
            datcol = data[column]
            if len(datcol) == 14 and isinstance(datcol, list) is True:
                # this is a special case for the stepped sine benchmark:
                for i in range(0, len(datcol), 1):
                    float_array.extend((datcol[i]))
            else:
                float_array = [float(string) for string in data[column]]
        return float_array

    # separate file
    def load_json_freq(self, filepath: str = "benchmark"):
        """ Function to load the frequency data from a .json file

        Args:
            filepath (str): the filepath of the .json file

        Returns:
            float_array (list): the frequency data from the .json file
        """
        with open(filepath) as f:
            data = json.load(f)
            float_array = [float(string) for string in data["Freq(Hz)"]]
        return float_array

    # separate file
    def list_dev_calc(self, bench_array, decoded_array):
        """ Function to calculate the deviation between the decoded and
        benchmark data

        This doesn't perform absolute value as if we want to plot this and
        see if its overperforming or underperforming we need to keep some
        flexibility

        Args:
            bench_array (list): the benchmark data
            decoded_array (list): the decoded data

        Returns:
            diff_list (list): the deviation between the decoded and benchmark
            data
        """
        diff_list = []
        for i in range(len(bench_array)):
            diff_list.append(float(bench_array[i]) - float(decoded_array[i]))
        return diff_list

    # separate file
    def list_abs_value(self, non_abs_array):
        """ Function to make all values in the list absolute

        Args:
            non_abs_array (list): the list to be converted to absolute values

        Returns:
            abs_array (list): the absolute value of the list

        """
        abs_array = [abs(element) for element in non_abs_array]
        return abs_array

    # this might need to be moved to a separate file
    def unit_pass_fail(self, diff_list, PFthreshold: float = 25.0,
                       fail_count: int = 900):
        """ Function to check if any value in the SPL falls
            outside of the accepted range

            reads in an array that has alreay been converted to absolute value.
            Then checks each value against the set P/F threshold to see if the
            unit has passed the test

            to account for any random noise in the data, a specific
            number of failed tests is allowed before the unit
            fails the P/F test

            fail_count is set to 540 because that is 1% of the 54000
            values that exist in the array being checkeed

        Variables:
            PF (bool): True if the unit passes the P/F test, False if not
            start_freq (float): the starting frequency of the SPL sweep
            start_index (int): the index at which the sweep data
                starts being useful for the P/F test
            freq_step (float): the frequency step of the sweep
            list_start (int): the index at which the sweep data
                starts being useful for the P/F test

        Args:
            abs_array (list): the list being checked
            PFthreshold (float): the threshold to be measured against
            fail_count (int): the number of failures allowed before the
                unit fails the P/F test

        Returns:
            PF (bool): True if the list is less than the threshold,
            False if not

        """
        PF = True
        len(diff_list)
        start_freq = 2.1972656
        start_index = 30
        end_index = 10000
        freq_step = 0.36621097
        list_start = round((start_index-start_freq)/freq_step)
        list_end = round((end_index-start_freq)/freq_step)
        number_failed = 0
        abs_list = self.list_abs_value(diff_list)
        for i in range(len(abs_list[list_start:list_end])):
            if abs_list[i] > PFthreshold:
                number_failed += 1
        if (number_failed > fail_count) or len(diff_list) < 54000:
            PF = False
        return PF

    # functions below this line are not used in the current version of the
    # code but are left in for future use

    def stepped_sine_pass_fail(self, diff_list, PFthreshold: float = 25.0,
                               fail_count: int = 900):
        """This function is used to check if any value in the SPL falls
            outside of the accepted range for the stepped sine sweep test

            reads in an array that has alreay been converted to absolute value.
            Then checks each value against the set P/F threshold to see if the
            unit has passed the test

            to account for any random noise in the data, a specific
            number of failed tests is allowed before the unit
            fails the P/F test

            fail_count is set to 540 because that is 1% of the 54000
            values that exist in the array being checkeed

            Variables:
                PF (bool): True if the unit passes the P/F test, False if not
                start_freq (float): the starting frequency of the SPL sweep
                start_index (int): the index at which the sweep data
                    starts being useful for the P/F test
                freq_step (float): the frequency step of the sweep
                list_start (int): the index at which the sweep data
                    starts being useful for the P/F test

        Args:
            abs_array (list): the list being checked
            PFthreshold (float): the threshold to be measured against
            fail_count (int): the number of failures allowed before the
                unit fails the P/F test

        Returns:
            PF (bool): True if the list is less than the threshold,
            False if not
        """
        PF = True
        len(diff_list)
        start_freq = 2.1972656
        start_index = 30
        end_index = 10000
        freq_step = 0.36621097
        list_start = round((start_index-start_freq)/freq_step)
        list_end = round((end_index-start_freq)/freq_step)
        number_failed = 0
        abs_list = self.list_abs_value(diff_list)
        for i in range(len(abs_list[list_start:list_end])):
            if abs_list[i] > PFthreshold:
                number_failed += 1
        if (number_failed > fail_count) or (len(diff_list) < 54000):
            PF = False
        return PF

    def get_measure_sweep_configuration(self):
        """ Function to get the current sweep configuration

        Args:
            None

        Returns:
            sweep configuration (dict): the current sweep configuration
        """
        get_response = self.get_request("/measure/sweep/configuration")
        return get_response

    def get_measure_commands(self):
        """ Function to get all measurement commands

        Args:
            None

        Returns:
            measurement commands (dict): all measurement commands
        """
        get_response = self.get_request("/measure/commands")
        return get_response

    def get_input_levels_commands(self):
        """ Function to get all input levels commands

        Args:
            None

        Returns:
            input levels commands (dict): all input levels commands
        """
        get_response = self.get_request("/input-levels/commands")
        return get_response

    # this should go in a separate file
    # This doesn't even work super well i will return to give it a proper
    # copmment later
    # something wrong with decoded array, it is one value too large
    # def plot_data(self, benchmark_array, decoded_array, filepath):
        # freq_array = self.load_json_freq(filepath)
        # plt.xscale('log', base=10)
        # plt.plot(freq_array, decoded_array[:-1], 'r--')
        # plt.plot(freq_array, benchmark_array, 'b--')
        # plt.fill_between(freq_array, decoded_array[:-1], benchmark_array,
        #                  color='grey', alpha=0.5)
        # plt.show()

    # this should go in a separate file
    def get_bmark(self, filepath):
        """ Function to get the benchmark data
            Case 1 is the tactile benchmark
            Case 2 is the audio benchmark

        Args:
            filepath (str): the filepath of the .json file

        Returns:
            benchmark_array (list): the benchmark data
        """
        match filepath:
            case 1:
                filepath = "./benchmarks/benchmark-vibration.json"
            case 2:
                filepath = "./benchmarks/benchmark-acoustic.json"
            case 3:
                filepath = "./benchmarks/stepped-sine benchmark.json"
            case 4:
                filepath = "./benchmarks/stepped-sine benchmark.json"
            case _:
                print("Filepath not found")
        return filepath

    def get_unit_type(self, unitType: str):
        """ Function to conver clean the user input and return
            the unit type in a uniform manner

        Args:
            unitType (str): the user input for the unit type

        Returns:
            unitType (str): One of the following: ResonX(r/R),
                            Bass Shaker(b/B),
                            Exciter(e/E), Thruster(t/T)
        """
        unitType = unitType.lower()
        while True:
            match unitType:
                case "r":
                    unitType = "ResonX"
                    break
                case "b":
                    unitType = "Bass Shaker"
                    break
                case "e":
                    unitType = "Exciter"
                    break
                case "t":
                    unitType = "Thruster"
                    break
                case _:
                    print("Invalid unit type")

        return unitType

    def make_json(self, name, freq_array, decoded_array, measurements, i,
                  filepath: str = None):
        """ Function to make a .json file from the decoded data

        Args:
            name (str): the name of the measurement given by user
            freq_array (list): the frequency data
            decoded_array (list): the decoded data for SPL data
            filepath (str): the filepath of the .json file

        Returns:
            N/A
        """
        mea = measurements
        outDict = {
                    "filename": name,
                    "Freq(Hz)": freq_array,
                    "SPL(dB)": decoded_array,
                    "Meta Data": {
                                    "REW Version": mea[i]["rewVersion"],
                                    "Dated": mea[i]["date"],
                                    "UUID": mea[i]["uuid"],
                                    "notes": mea[i]["notes"],
                                    "Measurement": mea[i]["title"],
                                    "Start Frequency": mea[i]["startFreq"],
                                    "End Frequency": mea[i]["endFreq"],
                                    }
                    }

        ensure_data_dirs()
        out_dir = get_json_dir() if filepath is None else filepath
        safe_name = self.sanitize_filename(name)
        file_path = os.path.join(str(out_dir), f"{safe_name}.json")
        with open(file_path, 'w') as outFile:
            json.dump(outDict, outFile, indent=4)
        return

    def make_stepped_json(self, name, dist_data, measurements, i,
                          filepath: str = None):
        """This function is used to make a .json file from the decoded data
        for stepped sine sweep measurements
        Args:
            name (str): the name of the measurement given by user
            decoded_data (list): the decoded data for SPL data
            filepath (str): the filepath of the .json file
        Returns:
            N/A
        """
        mea = measurements
        # have like for loop checking for all the data pieces in measurements
        # add the data pieces to a temp meta dict
        # then add the temp meta dict to the outDict
        outDict = {
                    "filename": name,
                    "Freq(Hz)": dist_data[0::15],
                    "Fundamental (dB)": dist_data[1::15],
                    "THD(%)": dist_data[2::15],
                    "THD+N(%)": dist_data[3::15],
                    "N(%)": dist_data[4::15],
                    "Noise (%)": dist_data[5::15],
                    "H2 (%)": dist_data[6::15],
                    "H3 (%)": dist_data[7::15],
                    "H4 (%)": dist_data[8::15],
                    "H5 (%)": dist_data[9::15],
                    "H6 (%)": dist_data[10::15],
                    "H7 (%)": dist_data[11::15],
                    "H8 (%)": dist_data[12::15],
                    "H9 (%)": dist_data[13::15],
                    "H10 (%)": dist_data[14::15],
                    "Meta Data": {
                                    "Measurement": mea[i]["title"],
                                    "Notes": mea[i]["notes"],
                                    "Date": mea[i]["date"],
                                    "uuid": mea[i]["uuid"],
                                    "rew version": mea[i]["rewVersion"],
                                    "Start Frequency": mea[i]["startFreq"],
                                    "End Frequency": mea[i]["endFreq"],
                                    }
                    }
        ensure_data_dirs()
        out_dir = get_stepped_sine_dir() if filepath is None else filepath
        safe_name = self.sanitize_filename(name)
        file_path = os.path.join(str(out_dir), f"{safe_name}.json")
        with open(file_path, 'w') as outFile:
            json.dump(outDict, outFile, indent=4)
        return

    def make_marimo_json(self, filename, measurement, decoded_array,
                         freq_array=None,
                         smoothing=None,
                         filepath: str = None):
        """ Function to make a .json file from the decoded data

        Args:
            name (str): the name of the measurement given by user
            freq_array (list): the frequency data
            decoded_array (list): the decoded data for SPL data
            filepath (str): the filepath of the .json file

        Returns:
            N/A
        """
        mea = measurement
        outDict = {
                    "filename": filename,
                    "Freq(Hz)": freq_array,
                    "SPL(dB)": decoded_array,
                    "Meta Data": {
                                    "REW Version": mea["rewVersion"],
                                    "Dated": mea["date"],
                                    "UUID": mea["uuid"],
                                    "notes": mea["notes"],
                                    "Measurement": mea["title"],
                                    "Start Frequency": mea["startFreq"],
                                    "End Frequency": mea["endFreq"],
                                    "Smoothing": smoothing,
                                    }
                    }

        ensure_data_dirs()
        out_dir = get_json_dir() if filepath is None else filepath
        safe_name = self.sanitize_filename(filename)
        file_path = os.path.join(str(out_dir), f"{safe_name}.json")

        with open(file_path, 'w') as outFile:
            outFile.write(
                jsonpickle.encode(outDict, indent=4)
            )
        print(f"writing to: {filepath}")
        return


if __name__ == "__main__":
    current_script_path = __file__
    print(f'wrong file: {current_script_path}')
    print("This file is not meant to be run directly.")
    print("Please run the main script instead.")
