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
    from project_paths import get_mdat_dir, get_json_dir, ensure_data_dirs
    import marimo as mo
    import pathlib as Path
    import time
    from datetime import datetime


@app.cell
def _():
    mo.md(r"""
    # REW Sweep + Export Tool
    ---

    This notebook guides you through:
    1. Loading a `.mdat` file
    2. Running sweeps
    3. Saving measurements in REW
    4. Exporting a JSON file
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## Setup
    ---
    Connect to REW and initialize the automation helper classes.
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
        ensure_data_dirs()
    return dataH, rewA, rewM


@app.cell
def _():
    mo.md(r"""
    ## Load .mdat files
    ---
    Choose a REW measurement file to load.
    """)
    return


@app.cell
def _():
    mo.md(rf"""
    **Data folder:** `{str(get_mdat_dir().parent)}`
    """)
    return


@app.cell
def _():
    file_browser = mo.ui.file_browser(
        initial_path=str(get_mdat_dir()),
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
    mo.md(r"""
    ## Unit Info
    ---
    Provide the unit type and number that will be embedded in the measurement name.
    """)
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
    mo.md(r"""
    ## Amplifier (Optional)
    ---
    Enter the amplifier IP if needed for your setup.
    """)
    return


@app.cell
def _():
    amp_ip_address = mo.ui.text(label="Enter LEA Amplifier IP Address:")
    amp_ip_address
    return


@app.cell
def _():
    mo.md(r"""
    ## Run Measurement
    ---
    Choose a sweep type to run the measurement.
    """)
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
    mo.md(r"""
    ## Save in REW
    ---
    Save the measurements inside REW.
    """)
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
def _(dataH, rewA, save_button, save_file_name):
    if save_button.value:
        safe_save_name = dataH.sanitize_filename(save_file_name.value)
        rewA.post_measurements_command_saveall(safe_save_name)
    else:
        print("No file saved")
    return


@app.cell
def _():
    mo.md(r"""
    ## Export JSON
    ---
    Select a measurement and export it as JSON.
    """)
    return


@app.cell
def _(measurements_all):
    measurement_items = []
    for _meas_id, _meas in measurements_all.items():
        title = _meas.get("title", f"Measurement {_meas_id}")
        measurement_items.append((int(_meas_id), f"{_meas_id}: {title}"))
    measurement_items.sort(key=lambda x: x[0])
    measurement_labels = [label for _, label in measurement_items]

    measurement_label_select = mo.ui.dropdown(
        options=measurement_labels,
        value=measurement_labels[0] if measurement_labels else None,
        label="Select measurement",
    )
    measurement_label_select
    return (measurement_label_select,)


@app.cell
def _(measurement_label_select):
    selected_label = measurement_label_select.value or ""
    selected_id = selected_label.split(":", 1)[0].strip() if selected_label else ""
    export_json_name_value = selected_label.split(":", 1)[1].strip() if ":" in selected_label else ""
    return export_json_name_value, selected_id


@app.cell
def _():
    mo.md(r"""
    ### Smoothing (optional)
    Select a smoothing option to apply to the frequency response.
    """)
    return


@app.cell
def _(rewA):
    smoothing_choices_raw = rewA.get_measurements_frequency_response_smoothing_choices()
    # smoothing_choices_raw
    return (smoothing_choices_raw,)


@app.cell
def _(smoothing_choices_raw):
    smoothing_options = ["Default"]
    smoothing_choices_list = smoothing_choices_raw
    if isinstance(smoothing_choices_list, dict):
        smoothing_choices_list = smoothing_choices_list.get(
            "choices",
            smoothing_choices_list.get("options", []),
        )
    if isinstance(smoothing_choices_list, list):
        for item in smoothing_choices_list:
            if isinstance(item, dict):
                value = item.get("value")
                if value is not None:
                    smoothing_options.append(str(value))
            else:
                smoothing_options.append(str(item))
    smoothing_select = mo.ui.dropdown(
        options=smoothing_options,
        value="Default",
        label="Smoothing",
    )
    smoothing_select
    return (smoothing_select,)


@app.cell
def _(load_button, rewA):
    mo.stop(not load_button.value, mo.md("click the button to continue"))

    time.sleep(3)
    with mo.status.spinner(title="Fetching data..."):
        measurements_all = rewA.get_measurements()
    return (measurements_all,)


@app.cell
def _(selected_id):
    measNum = str(selected_id)
    # measNum
    return (measNum,)


@app.cell
def _(measNum, measurements_all):
    measurement = measurements_all[measNum]
    # measurement
    return (measurement,)


@app.cell
def _(export_json_name_value, measNum, measurement, rewA, smoothing_select):
    rewVersion = measurement["rewVersion"]
    selected_smoothing = smoothing_select.value
    if selected_smoothing == "Default":
        selected_smoothing = None
    response = rewA.get_measurements_id_freq_response(
        measNum,
        smoothing=selected_smoothing,
    )
    rmag = response["magnitude"]
    dummy=export_json_name_value
    # response, rewVersion
    selected_smoothing
    response
    return response, selected_smoothing


@app.cell
def _(dataH, response):
    decoded_array = dataH.decode_array(response["magnitude"])
    # decoded_array
    return (decoded_array,)


@app.cell
def _(dataH, decoded_array, response):
    freq_array = dataH.build_freq_array_from_response(response, len(decoded_array))
    # freq_array
    return (freq_array,)


@app.cell
def _():
    json_outpath = str(get_json_dir())
    json_outpath
    return (json_outpath,)


@app.cell
def _(measurement):
    measurement['rewVersion']
    return


@app.cell
def _(export_json_name_value):
    mo.stop(not export_json_name_value, mo.md("Select a measurement to continue."))

    make_json_button = mo.ui.run_button(label='make the json')
    make_json_button
    return (make_json_button,)


@app.cell
def _(
    dataH,
    decoded_array,
    export_json_name_value,
    freq_array,
    json_outpath,
    make_json_button,
    measurement,
    response,
    selected_smoothing,
):
    mo.stop(not export_json_name_value)
    if make_json_button.value:
        smoothing = response.get("smoothing") if isinstance(response, dict) else None
        if selected_smoothing:
            smoothing = selected_smoothing
        dataH.make_marimo_json(
            export_json_name_value,
            measurement,
            decoded_array,
            freq_array,
            smoothing=smoothing,
            filepath=json_outpath,
        )
    else:
        print('not json yet')
    return


@app.cell
def _():
    mo.md(r"""
    ### Export All Measurements
    Export all measurements into a timestamped folder under `data/json`.
    """)
    return


@app.cell
def _():
    export_all_button = mo.ui.run_button(label="Export All Measurements")
    export_all_button
    return (export_all_button,)


@app.cell
def _(dataH, export_all_button, measurements_all, rewA):
    mo.stop(not export_all_button.value, mo.md("Click to export all measurements."))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_all_dir = get_json_dir() / f"export_{timestamp}"
    export_all_dir.mkdir(parents=True, exist_ok=True)

    for _meas_id, _meas in measurements_all.items():
        response_all = rewA.get_measurements_id_freq_response(str(_meas_id))
        decoded_array_all = dataH.decode_array(response_all["magnitude"])
        freq_array_all = dataH.build_freq_array_from_response(
            response_all,
            len(decoded_array_all),
        )
        smoothing_all = response_all.get("smoothing") if isinstance(response_all, dict) else None
        filename_all = _meas.get("title", f"measurement_{_meas_id}")
        dataH.make_marimo_json(
            filename_all,
            _meas,
            decoded_array_all,
            freq_array_all,
            smoothing=smoothing_all,
            filepath=str(export_all_dir),
        )

    mo.md(rf"Exported to: `{str(export_all_dir)}`")
    return


@app.cell
def _():
    mo.md(r"""
    ## Exit
    ---
    Shut down REW when finished.
    """)
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
