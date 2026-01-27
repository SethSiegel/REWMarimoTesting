# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.0",
#     "pyzmq>=27.1.0",
#     "requests>=2.32.5",
# ]
# ///

import marimo

__generated_with = "0.19.6"
app = marimo.App()

with app.setup:
    from REWAutomation import REWAutomation
    from data_handling import Data_Handling
    from LEA_controls import Lea_Settings
    from REW_measurements import Measurements
    import marimo as mo
    import pathlib as Path
    # import time



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
    return rewA, rewM


@app.cell
def _():
    file_browser = mo.ui.file_browser(
        initial_path=r"C:\Users\Seth\Documents\Temporary_Files",
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
    export_button = mo.ui.button(label="Export as JSON")
    export_button
    return (export_button,)


@app.cell
def _(export_button, rewA, save_file_name):
    if export_button.value:
        rewA.post_measurements_command_saveall(save_file_name.value)
    else:
        print("No files exported")
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
