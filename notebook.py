# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jsonpickle>=4.1.1",
#     "marimo>=0.19.0",
#     "pyzmq>=27.1.0",
#     "requests>=2.32.5",
# ]
# ///

import marimo

__generated_with = "0.19.7"
app = marimo.App()

with app.setup:
    from REWAutomation import REWAutomation
    from data_handling import Data_Handling
    from LEA_controls import Lea_Settings
    from REW_measurements import Measurements
    import marimo as mo
    import pathlib as Path
    import time


@app.cell
def _():
    mo.md(r"""
    import statements
    """)
    return


@app.cell
def _():
    mo.md(r"""
    Initial program setup
    """)
    return


@app.cell
def _():
    if __name__ == "__main__":
        # instantiate on local host port 4735

        # define names for the imported classes
        rewA = REWAutomation()
        dataH = Data_Handling()
        Lea = Lea_Settings()
        rewM = Measurements(rewA, dataH, Lea)

        '''
        will need to change this to the correct ip address
        for each testing tool that is setup
        '''
        # ip address and port for the LEA amplifier at Latham
        # Lea_address = 'ws://192.168.1.200:1234'
        # amp_name = Lea.return_amp_name(Lea_address)
        # Lea.websocket_connect(Lea_address, Lea.unmute())
        # Lea.websocket_connect(Lea_address, Lea.mute())
        # Lea.websocket_connect(Lea_address, Lea.unmute())

        while rewA.is_server_setup() is False:
            # wait for server to be ready
            pass

        ifDone = False
        stillRunning = True
        calcsWanted = False
        measurements = ""
        measurements_taken = 0

        # manually set the last microphone input
        # this can be changed to allow for more microphones to be added
        last_input = "2: Dante rx 2"

        # the last input should always be the acoustic microphone
        num_of_mics = int(last_input[0])

        # getting the audio drivers established and setting the last input
        print("Setting audio drivers, please wait")
        # rewA.post_audio_driver()
        # rewA.post_audio_device()
        # for i in range(num_of_mics-1):
            # rewA.post_audio_asio_input(f"{i+1}: Dante rx {i+1}")
            # rewA.post_audio_asio_output(f"{i+1}: Dante tx {i+1}")
        rewA.post_no_overall_average()
        print("Audio drivers set")
    return dataH, rewA, rewM


@app.cell
def _():
    file_browser = mo.ui.file_browser(
        initial_path=r"C:\Users\Seth\Documents\rew_marimo_data\mdat",
        multiple=False
    )
    file_browser
    return (file_browser,)


@app.cell
def _(file_browser):
    fileName = file_browser.path(index=0)
    path_str = str(fileName).replace("\\", "/")
    path_str
    return (path_str,)


@app.cell
def _():
    load_button = mo.ui.run_button(label="Load mdat file")
    load_button
    return (load_button,)


@app.cell
def _(load_button, path_str, rewA):
    if load_button.value:
        rewA.load_mdat(path_str)
    else:
        print("No file loaded")
    return


@app.cell
def _():
    unitType = mo.ui.text(label="What type of unit is this?:")
    unitType
    return (unitType,)


@app.cell
def _():
    unitNumber = mo.ui.text(label="What number unit is this?:")
    unitNumber
    return (unitNumber,)


@app.cell
def _():
    amp_ip_address = mo.ui.text(label="Enter LEA Amplifier IP Address:")
    amp_ip_address
    return


@app.cell
def _():
    sine_sweep_button = mo.ui.run_button(label="Sine Sweep")
    stepped_sine_sweep_button = mo.ui.run_button(label="Stepped Sine Sweep")
    sine_sweep_button, stepped_sine_sweep_button
    return sine_sweep_button, stepped_sine_sweep_button


@app.cell
def _(
    rewM,
    sine_sweep_button,
    stepped_sine_sweep_button,
    unitNumber,
    unitType,
):
    if sine_sweep_button.value:
        rewM.sine_sweep(rewM.unitInput(unitType.value, unitNumber.value))
    elif stepped_sine_sweep_button.value:
        rewM.stepped_sine_sweep(rewM.unitInput(unitType.value, unitNumber.value))
    else:
        with mo.redirect_stdout():
            print('Click a button!')
    return


@app.cell
def _():
    save_file_name = mo.ui.text(label="What do you want to name the file?:")
    save_file_name
    return (save_file_name,)


@app.cell
def _():
    save_button = mo.ui.run_button(label="Save Measurements")
    save_button
    return (save_button,)


@app.cell
def _(rewA, save_button, save_file_name):
    if save_button.value:
        rewA.post_measurements_command_saveall(save_file_name.value)
    else:
        print("No file saved")
    return


@app.cell
def _():
    export_json_name = mo.ui.text(label="What do you want to call the exported JSON?:")
    export_json_name
    return (export_json_name,)


@app.cell
def _(load_button, rewA):
    mo.stop(not load_button.value, mo.md("click the button to continue"))

    time.sleep(3)
    with mo.status.spinner(title="Fetching data..."):
        measurements_all = rewA.get_measurements()
    return (measurements_all,)


@app.cell
def _():
    measurement_number_to_export = mo.ui.number(start=1, stop=100, step=1, label="select number")
    measurement_number_to_export
    return (measurement_number_to_export,)


@app.cell
def _(measurement_number_to_export):
    measNum = str(measurement_number_to_export.value)
    return (measNum,)


@app.cell
def _(measNum, measurements_all):
    measurement = measurements_all[measNum]
    measurement
    return (measurement,)


@app.cell
def _(measurement, rewA):
    rewVersion = measurement["rewVersion"]
    response = rewA.get_measurements_id_freq_response("1")
    rmag = response["magnitude"]
    response, rewVersion
    return (response,)


@app.cell
def _(dataH, response):
    decoded_array = dataH.decode_array(response["magnitude"])
    decoded_array
    return (decoded_array,)


@app.cell
def _():
    json_outpath = r"C:\Users\Seth\Documents\rew_marimo_data\json"
    json_outpath
    return (json_outpath,)


@app.cell
def _(measurement):
    measurement['rewVersion']
    return


@app.cell
def _():
    mo.md(r"""
    #TODO: figure out way to get the right frequency data to store in the json alongside the magnitude data
    """)
    return


@app.cell
def _():
    make_json_button = mo.ui.run_button(label='make the json')
    make_json_button
    return (make_json_button,)


@app.cell
def _(
    dataH,
    decoded_array,
    export_json_name,
    json_outpath,
    make_json_button,
    measurement,
):
    if make_json_button.value:
        dataH.make_marimo_json(export_json_name.value, measurement, decoded_array, freq_array=None, filepath=json_outpath)
    else:
        print('not json yet')
    return


@app.cell
def _():
    mo.md(r"""
    #NOTE: add function to save measurements individually and show the measurements in a dropdown list like the files that can be loaded in

    need to fix up the make_json function so that it works better with the response from the webapp and then I can just set it to run in a loop for the number of measurements that are selected to be exported
    """)
    return


@app.cell
def _():
    # if export_all_button.value:
    #     rewA.post_measurements_command_saveall(save_file_name.value)
    # elif export_single_button.value:
    #     dataH.make_json(save_file_name.value, freq_array, decoded_array,
    #                     measurements, i)
    # else:
    #     print("No files exported")
    return


@app.cell
def _():
    exit_REW_button = mo.ui.run_button(label="exit REW?")
    exit_REW_button
    return (exit_REW_button,)


@app.cell
def _(exit_REW_button, rewA):
    if exit_REW_button.value:
        rewA.post_command_shutdown()
        print("REW is shut down")
    else:
        print("REW is not shut down")
    return


if __name__ == "__main__":
    app.run()
