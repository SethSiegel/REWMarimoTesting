# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jsonpickle>=4.1.1",
#     "marimo>=0.19.0",
#     "pyzmq>=27.1.0",
#     "requests>=2.32.5",
# ]
# [tool.marimo.opengraph]
# title = "REW Sweep + Export Tool"
# description = "REW measurement automation and LEA calibration interface."
# image = "https://www.roomeqwizard.com/help/images/REW%20logo.png"
# ///

import marimo

__generated_with = "0.19.7"
app = marimo.App(app_title="REW Sweep + Export Tool")

with app.setup:
    import sys
    import pathlib as _pathlib
    repo_root = _pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

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

    End-to-end workflow:
    1. Launch/attach REW session
    2. Optional I/O calibration
    3. Load `.mdat`
    4. Set naming fields
    5. Run sweeps
    6. Save `.mdat` in REW
    7. Export JSON (single or all)
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## 1) REW Session
    ---
    Start by launching or attaching to REW.
    Use session controls here for launch, clear, and shutdown.
    """)
    return


@app.cell
def _():
    rew_launch_button = mo.ui.run_button(label="Launch / Attach REW")
    clear_rew_measurements_button = mo.ui.run_button(label="Clear All Measurements")
    exit_rew_session_button = mo.ui.run_button(label="Shutdown REW")
    session_controls = mo.hstack(
        [rew_launch_button, clear_rew_measurements_button, exit_rew_session_button]
    )
    session_controls
    return clear_rew_measurements_button, exit_rew_session_button, rew_launch_button


@app.cell
def _():
    rew_runtime_state, set_rew_runtime_state = mo.state(
        {
            "rewA": None,
            "rewM": None,
            "status": "not_launched",
            "error": "",
        }
    )
    return rew_runtime_state, set_rew_runtime_state


@app.cell
def _(rew_launch_button, rew_runtime_state, set_rew_runtime_state):
    dataH = Data_Handling()
    Lea = Lea_Settings()
    _rew_runtime = rew_runtime_state()
    rewA = _rew_runtime.get("rewA")
    rewM = _rew_runtime.get("rewM")
    rew_launch_status = _rew_runtime.get("status", "not_launched")
    rew_launch_error = _rew_runtime.get("error", "")

    if rew_launch_button.value:
        try:
            if rewA is None:
                rewA = REWAutomation()
            if not rewA.is_server_setup():
                rew_launch_status = "failed"
                rew_launch_error = (
                    "REW API not detected. If REW is already open, ensure it is "
                    "an API-enabled instance on the configured port."
                )
                rewA = None
                rewM = None
            else:
                rewA.post_no_overall_average()
                ensure_data_dirs()
                rewM = Measurements(rewA, dataH, Lea)
                rew_launch_status = "ready"
                rew_launch_error = ""
        except Exception as _rew_launch_exc:
            rew_launch_status = "failed"
            rew_launch_error = str(_rew_launch_exc)
            rewA = None
            rewM = None

        set_rew_runtime_state(
            {
                "rewA": rewA,
                "rewM": rewM,
                "status": rew_launch_status,
                "error": rew_launch_error,
            }
        )

    return dataH, rewA, rewM, rew_launch_error, rew_launch_status


@app.cell
def _(rew_launch_error, rew_launch_status):
    if rew_launch_status == "ready":
        rew_launch_status_widget = mo.md(
            "<span style='color: green; font-weight: 700;'>REW is ready.</span>"
        )
    elif rew_launch_status == "failed":
        rew_launch_status_widget = mo.md(
            "<span style='color: red; font-weight: 700;'>REW launch failed.</span>"
            f"  \n{rew_launch_error}"
        )
    else:
        rew_launch_status_widget = mo.md(
            "Press **Launch / Attach REW** before using REW actions."
        )
    rew_launch_status_widget
    return (rew_launch_status_widget,)


@app.cell
def _():
    clear_rew_result_state, set_clear_rew_result_state = mo.state(
        {
            "status": "idle",
            "note": "Clear-all action has not been run yet.",
        }
    )
    return clear_rew_result_state, set_clear_rew_result_state


@app.cell
def _(clear_rew_measurements_button, rewA, set_clear_rew_result_state):
    if clear_rew_measurements_button.value:
        if rewA is None:
            set_clear_rew_result_state(
                {
                    "status": "failed",
                    "note": "Launch REW first.",
                }
            )
        else:
            try:
                set_clear_rew_result_state(rewA.post_measurements_command_clearall())
            except Exception as _clear_exc:
                set_clear_rew_result_state(
                    {
                        "status": "failed",
                        "note": str(_clear_exc),
                    }
                )
    return


@app.cell
def _(clear_rew_result_state):
    _clear_rew_result = clear_rew_result_state()
    _clear_status = _clear_rew_result.get("status")
    if _clear_status == "idle":
        clear_rew_status_widget = mo.md(_clear_rew_result.get("note", ""))
    elif _clear_status == "failed":
        _note = _clear_rew_result.get("note")
        _error = _clear_rew_result.get("error")
        _response = _clear_rew_result.get("response")
        _available = _clear_rew_result.get("available_commands")
        _details = []
        if _note:
            _details.append(_note)
        if _error and _error not in _details:
            _details.append(_error)
        if _response:
            _details.append(f"Response: `{_response}`")
        if _available:
            _details.append(
                "Available commands: "
                + ", ".join(str(c) for c in _available[:10])
            )
        _detail_text = "  \n".join(_details) if _details else "Unknown error"
        clear_rew_status_widget = mo.md(
            "<span style='color: red; font-weight: 700;'>Clear all failed.</span>"
            f"  \n{_detail_text}"
        )
    else:
        clear_rew_status_widget = mo.md(
            "<span style='color: green; font-weight: 700;'>Clear all command sent.</span>"
            f"  \nCommand used: `{_clear_rew_result.get('command_used')}`"
            f"  \nResponse: `{_clear_rew_result.get('response')}`"
            f"  \n{_clear_rew_result.get('error', '')}"
        )
    clear_rew_status_widget
    return (clear_rew_status_widget,)


@app.cell
def _():
    rew_shutdown_result_state, set_rew_shutdown_result_state = mo.state(
        {
            "status": "idle",
            "note": "Shutdown action has not been run yet.",
        }
    )
    return rew_shutdown_result_state, set_rew_shutdown_result_state


@app.cell
def _(
    exit_rew_session_button,
    rew_runtime_state,
    set_rew_runtime_state,
    set_rew_shutdown_result_state,
):
    if exit_rew_session_button.value:
        _runtime = rew_runtime_state()
        _rewA_for_shutdown = _runtime.get("rewA")
        if _rewA_for_shutdown is None:
            set_rew_shutdown_result_state(
                {
                    "status": "failed",
                    "note": "REW is not running from this interface.",
                }
            )
        else:
            try:
                _shutdown_response = _rewA_for_shutdown.post_command_shutdown()
                set_rew_shutdown_result_state(
                    {
                        "status": "ok",
                        "note": "REW shutdown command sent.",
                        "response": _shutdown_response,
                    }
                )
                set_rew_runtime_state(
                    {
                        "rewA": None,
                        "rewM": None,
                        "status": "not_launched",
                        "error": "",
                    }
                )
            except Exception as _shutdown_exc:
                set_rew_shutdown_result_state(
                    {
                        "status": "failed",
                        "note": str(_shutdown_exc),
                    }
                )
    return


@app.cell
def _(rew_shutdown_result_state):
    _rew_shutdown_result = rew_shutdown_result_state()
    _rew_shutdown_status = _rew_shutdown_result.get("status")
    if _rew_shutdown_status == "idle":
        rew_shutdown_status_widget = mo.md(_rew_shutdown_result.get("note", ""))
    elif _rew_shutdown_status == "failed":
        rew_shutdown_status_widget = mo.md(
            "<span style='color: red; font-weight: 700;'>Shutdown failed.</span>"
            f"  \n{_rew_shutdown_result.get('note', 'Unknown error')}"
        )
    else:
        rew_shutdown_status_widget = mo.md(
            "<span style='color: green; font-weight: 700;'>Shutdown command sent.</span>"
            f"  \nResponse: `{_rew_shutdown_result.get('response')}`"
        )
    rew_shutdown_status_widget
    return (rew_shutdown_status_widget,)


@app.cell
def _(clear_rew_status_widget, rew_launch_status_widget, rew_shutdown_status_widget):
    rew_session_panel = mo.vstack(
        [
            mo.md("### Session Status"),
            rew_launch_status_widget,
            clear_rew_status_widget,
            rew_shutdown_status_widget,
        ]
    )
    rew_session_panel
    return


@app.cell
def _():
    mo.md(r"""
    ## 2) I/O Calibration
    ---
    Optional but recommended before loading `.mdat`.
    Runs generator tone + LEA readback and shows debug output.
    """)
    return


@app.cell
def _():
    io_calibration_ws = mo.ui.text(
        label="LEA WebSocket Address",
        value="ws://192.168.4.73:1234",
    )
    io_calibration_ws
    return (io_calibration_ws,)


@app.cell
def _():
    io_calibration_button = mo.ui.run_button(label="Run I/O Calibration")
    io_calibration_button
    return (io_calibration_button,)


@app.cell
def _():
    io_calibration_result_state, set_io_calibration_result_state = mo.state(
        {
            "status": "idle",
            "note": "Calibration has not been run yet.",
            "rew_calibrate_level_value_raw": None,
            "lea_measured_output_voltage_v": None,
            "rew_start_error": None,
        }
    )
    return io_calibration_result_state, set_io_calibration_result_state


@app.cell
def _(
    io_calibration_button,
    io_calibration_ws,
    rewM,
    set_io_calibration_result_state,
):
    mo.stop(not io_calibration_button.value, mo.md("Click **Run I/O Calibration** to start."))
    mo.stop(rewM is None, mo.md("Launch / Attach REW before calibration."))

    ws_value = io_calibration_ws.value.strip()
    if not ws_value:
        _io_calibration_result_run = {
            "status": "failed",
            "note": "LEA WebSocket address is required.",
        }
    else:
        try:
            with mo.status.spinner(title="Running I/O calibration..."):
                _io_calibration_result_run = rewM.REW_IO_Calibration(
                    Lea_address=ws_value,
                    channel=2,
                    frequency_hz=1000.0,
                    target_voltage_v=3.0,
                    tone_seconds=3.0,
                    lea_timeout_seconds=2.0,
                )
        except Exception as calibration_exc:
            _io_calibration_result_run = {
                "status": "failed",
                "note": str(calibration_exc),
            }

    set_io_calibration_result_state(_io_calibration_result_run)
    return


@app.cell
def _(io_calibration_result_state):
    _io_calibration_result_view = io_calibration_result_state()
    _status_text = _io_calibration_result_view.get("status", "idle")
    _debug_log_lines = _io_calibration_result_view.get("debug_log") or []
    if _debug_log_lines:
        _debug_md = "  \n".join([f"- {line}" for line in _debug_log_lines])
    else:
        _debug_md = "- No debug log entries."
    if _status_text == "idle":
        _status_md = (
            "Calibration has not been run yet."
            f"  \nDebug log:"
            f"  \n{_debug_md}"
        )
    elif _status_text == "ok":
        raw_value = _io_calibration_result_view.get("rew_calibrate_level_value_raw")
        if raw_value is None:
            raw_value = _io_calibration_result_view.get("lea_measured_output_voltage_v")
        rew_started = _io_calibration_result_view.get("rew_start_error") is None
        _status_md = (
            "<span style='color: green; font-weight: 700;'>Calibrated</span>"
            f"  \nREW generator started: `{rew_started}`"
            f"  \nRaw level value: `{raw_value}`"
            f"  \nDebug log:"
            f"  \n{_debug_md}"
        )
    else:
        failure_note = _io_calibration_result_view.get("note", "Calibration failed.")
        raw_value = _io_calibration_result_view.get("rew_calibrate_level_value_raw")
        if raw_value is None:
            raw_value = _io_calibration_result_view.get("lea_measured_output_voltage_v")
        rew_started = _io_calibration_result_view.get("rew_start_error") is None
        _status_md = (
            "<span style='color: red; font-weight: 700;'>Calibration failed</span>"
            f"  \n{failure_note}"
            f"  \nREW generator started: `{rew_started}`"
            f"  \nRaw level value: `{raw_value}`"
            f"  \nDebug log:"
            f"  \n{_debug_md}"
        )
    _calibration_status_widget = mo.md(_status_md)
    _calibration_status_widget
    return


@app.cell
def _():
    mo.md(r"""
    ## 3) Load .mdat
    ---
    Select one `.mdat` file, then click load.
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
def _(path_str):
    parent_mdat = None
    if path_str:
        _path = Path.Path(path_str)
        parent_mdat = _path.stem
    return (parent_mdat,)


@app.cell
def _():
    load_button = mo.ui.run_button(label="Load Selected .mdat")
    load_button
    return (load_button,)


@app.cell
def _(load_button, path_str, rewA):
    if load_button.value:
        if not path_str:
            print("Select an .mdat file first.")
        elif rewA is None:
            print("Launch / Attach REW first.")
        else:
            rewA.load_mdat(path_str)
    else:
        print("No file loaded")
    return


@app.cell
def _():
    mo.md(r"""
    ## 4) Unit Info
    ---
    Provide naming fields used when taking measurements.
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
def _(unitNumber, unitType):
    _unit_name = f"{unitType.value} {unitNumber.value}".strip()
    mo.md(rf"**Current measurement name:** `{_unit_name or '-'}`")
    return (_unit_name,)


@app.cell
def _():
    mo.md(r"""
    ## 5) Measurement Controls
    ---
    Choose sweep type and run measurement.
    """)
    return


@app.cell
def _():
    sine_sweep_button = mo.ui.run_button(label="Run Sine Sweep")
    stepped_sine_sweep_button = mo.ui.run_button(label="Run Stepped Sine Sweep")
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
    if rewM is None and (sine_sweep_button.value or stepped_sine_sweep_button.value):
        with mo.redirect_stdout():
            print("Launch / Attach REW first.")
    elif sine_sweep_button.value:
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
    ## 6) Save Loaded Measurements
    ---
    Save all currently loaded measurements in REW as one `.mdat`.
    """)
    return


@app.cell
def _():
    save_file_name = mo.ui.text(label="Save .mdat filename")
    save_file_name
    return (save_file_name,)


@app.cell
def _():
    save_button = mo.ui.run_button(label="Save All to .mdat")
    save_button
    return (save_button,)


@app.cell
def _(dataH, rewA, save_button, save_file_name):
    if save_button.value:
        if rewA is None:
            print("Launch / Attach REW first.")
        else:
            safe_save_name = dataH.sanitize_filename(save_file_name.value)
            rewA.post_measurements_command_saveall(safe_save_name)
    else:
        print("No file saved")
    return


@app.cell
def _():
    mo.md(r"""
    ## 7) Export JSON
    ---
    Select a measurement and export it as JSON.
    Filenames use `YYYYMMDD_HHMMSS__ID<id>__<title>.json`.
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
    if rewA is None:
        smoothing_choices_raw = []
    else:
        smoothing_choices_raw = rewA.get_measurements_frequency_response_smoothing_choices()
    # smoothing_choices_raw
    return (smoothing_choices_raw,)


@app.cell
def _(smoothing_choices_raw):
    smoothing_options = ["Default"]
    smoothing_label_to_value = {"Default": None}
    smoothing_choices_list = smoothing_choices_raw
    if isinstance(smoothing_choices_list, dict):
        smoothing_choices_list = smoothing_choices_list.get(
            "choices",
            smoothing_choices_list.get("options", []),
        )
    if isinstance(smoothing_choices_list, list):
        for item in smoothing_choices_list:
            if isinstance(item, dict):
                value = item.get("value", item.get("id"))
                label = item.get("label", item.get("name", value))
                if label is None and value is None:
                    continue
                label = str(label) if label is not None else str(value)
                smoothing_options.append(label)
                smoothing_label_to_value[label] = value
            else:
                label = str(item)
                smoothing_options.append(label)
                smoothing_label_to_value[label] = item
    smoothing_select = mo.ui.dropdown(
        options=smoothing_options,
        value="Default",
        label="Smoothing",
    )
    smoothing_select
    return smoothing_label_to_value, smoothing_select


@app.cell
def _(load_button, rewA):
    if load_button.value:
        if rewA is None:
            measurements_all = {}
        else:
            time.sleep(3)
            with mo.status.spinner(title="Fetching data..."):
                measurements_all = rewA.get_measurements()
    else:
        measurements_all = {}
    return (measurements_all,)


@app.cell
def _(selected_id):
    measNum = str(selected_id)
    # measNum
    return (measNum,)


@app.cell
def _(measNum, measurements_all):
    measurement = measurements_all.get(measNum, {})
    # measurement
    return (measurement,)


@app.cell
def _(
    export_json_name_value,
    measNum,
    measurement,
    rewA,
    smoothing_label_to_value,
    smoothing_select,
):
    response = {}
    selected_smoothing = None
    if rewA is not None and measNum and measurement:
        smoothing_label = smoothing_select.value if smoothing_select else "Default"
        selected_smoothing = smoothing_label_to_value.get(smoothing_label)
        if selected_smoothing is not None:
            selected_smoothing = str(selected_smoothing)
        response = rewA.get_measurements_id_freq_response(
            measNum,
            smoothing=selected_smoothing,
        )
    _ = export_json_name_value
    # response, rewVersion
    selected_smoothing
    response
    return response, selected_smoothing


@app.cell
def _(dataH, response):
    magnitude = response.get("magnitude") if isinstance(response, dict) else None
    decoded_array = dataH.decode_array(magnitude) if magnitude else []
    # decoded_array
    return (decoded_array,)


@app.cell
def _(dataH, decoded_array, response):
    freq_array = []
    if decoded_array and isinstance(response, dict):
        freq_array = dataH.build_freq_array_from_response(response, len(decoded_array))
    # freq_array
    return (freq_array,)


@app.cell
def _(dataH, parent_mdat):
    _mdat_folder_name = dataH.sanitize_filename(parent_mdat or "unknown_mdat")
    json_outpath = str(get_json_dir() / _mdat_folder_name)
    json_outpath
    return (json_outpath,)


@app.cell
def _(measurement):
    _version = measurement.get("rewVersion", "") if isinstance(measurement, dict) else ""
    if _version:
        mo.md(f"REW version (from measurement): `{_version}`")
    else:
        mo.md("REW version (from measurement): unavailable")
    return


@app.cell
def _(export_json_name_value):
    mo.stop(not export_json_name_value, mo.md("Select a measurement to continue."))

    make_json_button = mo.ui.run_button(label="Export Selected Measurement as JSON")
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
    measNum,
    parent_mdat,
):
    mo.stop(not export_json_name_value)
    if make_json_button.value:
        smoothing = response.get("smoothing") if isinstance(response, dict) else None
        if selected_smoothing:
            smoothing = selected_smoothing
        _timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _base_name = f"{_timestamp}__ID{measNum}__{export_json_name_value}"
        _export_name = dataH.sanitize_filename(_base_name)
        dataH.make_marimo_json(
            _export_name,
            measurement,
            decoded_array,
            freq_array,
            smoothing=smoothing,
            parent_mdat=parent_mdat,
            filepath=json_outpath,
        )
    else:
        print('not json yet')
    return


@app.cell
def _():
    mo.md(r"""
    ### Export All Measurements
    Export all measurements into `data/json/<parent_mdat>/` using the same naming scheme.
    """)
    return


@app.cell
def _():
    export_all_button = mo.ui.run_button(label="Export All Measurements")
    export_all_button
    return (export_all_button,)


@app.cell
def _(dataH, export_all_button, measurements_all, rewA, parent_mdat):
    mo.stop(not export_all_button.value, mo.md("Click to export all measurements."))
    mo.stop(rewA is None, mo.md("Launch / Attach REW first."))

    _mdat_folder_name = dataH.sanitize_filename(parent_mdat or "unknown_mdat")
    export_all_dir = get_json_dir() / _mdat_folder_name

    for _meas_id, _meas in measurements_all.items():
        response_all = rewA.get_measurements_id_freq_response(str(_meas_id))
        decoded_array_all = dataH.decode_array(response_all["magnitude"])
        freq_array_all = dataH.build_freq_array_from_response(
            response_all,
            len(decoded_array_all),
        )
        smoothing_all = response_all.get("smoothing") if isinstance(response_all, dict) else None
        filename_all = _meas.get("title", f"measurement_{_meas_id}")
        _timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _base_name = f"{_timestamp}__ID{_meas_id}__{filename_all}"
        _export_name = dataH.sanitize_filename(_base_name)
        dataH.make_marimo_json(
            _export_name,
            _meas,
            decoded_array_all,
            freq_array_all,
            smoothing=smoothing_all,
            parent_mdat=parent_mdat,
            filepath=str(export_all_dir),
        )

    mo.md(rf"Exported to: `{str(export_all_dir)}`")
    return


if __name__ == "__main__":
    app.run()
