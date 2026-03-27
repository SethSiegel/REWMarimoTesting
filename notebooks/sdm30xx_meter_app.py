# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.11",
#     "plotly>=5.22.0",
# ]
# [tool.marimo.opengraph]
# title = "SDM30xx Meter"
# description = "LAN-connected SDM30xx voltage/impedance sampling dashboard."
# image = "https://www.roomeqwizard.com/help/images/REW%20logo.png"
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(app_title="SDM30xx Meter")


with app.setup:
    import sys
    import os
    import time
    from datetime import datetime
    import pathlib as _pathlib
    import socket
    import math
    import plotly.graph_objects as go
    import marimo as mo

    repo_root = _pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from SDM30xx_SCPI import SDM30xx_SCPI
    from project_paths import _load_dotenv



@app.cell
def _():
    def sdm_safe_float(_value):
        try:
            return float(_value)
        except (TypeError, ValueError):
            return None

    def sdm_query_measurement(_client, _kind):
        if _client is None:
            return None, None, "", "No client connection."
        try:
            if _kind == "Impedance":
                _raw = _client.qeury_command("MEAS:FRES? 200")
                _unit = "ohm"
            else:
                _raw = _client.qeury_command("MEAS:VOLT?")
                _unit = "V"
        except Exception as _exc:
            return None, None, "", f"Query failed: {_exc}"

        _value = sdm_safe_float(_raw)
        _ok = _value is not None
        _note = "" if _ok else f"Invalid response: {_raw}"
        return _value, _raw, _unit, _note

    def sdm_close_client(_client):
        if _client is None:
            return
        try:
            _client.close()
        except Exception:
            return

    def sdm_test_connection(_ip, _port, _timeout=2.0):
        try:
            _sock = socket.create_connection((_ip, _port), timeout=_timeout)
            _sock.close()
            return True, ""
        except Exception as _exc:
            return False, str(_exc)

    return (
        sdm_close_client,
        sdm_query_measurement,
        sdm_safe_float,
        sdm_test_connection,
    )


@app.cell
def _():
    mo.md(
        r"""
        # SDM30xx Meter
        ---
        Live voltage or impedance sampling over LAN.  
        Set duration and sampling interval, then start a measurement to stream
        data into the table and plot.
        """
    )
    return


@app.cell
def _():
    _load_dotenv()
    multimeter_ip = os.getenv("MULTIMETER_IP") or ""
    
    sdm_ip_input = mo.ui.text(
        label="SDM30xx IP Address",
        value=multimeter_ip,
        full_width=True,
    )
    sdm_port_input = mo.ui.number(
        label="SDM30xx Port",
        value=5025,
        step=1,
        full_width=True,
    )
    mo.hstack([sdm_ip_input, sdm_port_input])
    return sdm_ip_input, sdm_port_input


@app.cell
def _():
    test_connection_button = mo.ui.run_button(
        label="Test Connection",
        full_width=True,
    )
    test_connection_button
    return (test_connection_button,)


@app.cell
def _():
    connection_test_state, set_connection_test_state = mo.state(
        {
            "status": "idle",
            "note": "Click Test Connection to check LAN access.",
        }
    )
    return connection_test_state, set_connection_test_state


@app.cell
def _(
    connection_test_state,
    sdm_ip_input,
    sdm_port_input,
    set_connection_test_state,
    test_connection_button,
    sdm_test_connection,
):
    if test_connection_button.value:
        _ip = (sdm_ip_input.value or "").strip()
        _port = int(sdm_port_input.value or 0)
        if not _ip:
            set_connection_test_state(
                {
                    "status": "failed",
                    "note": "IP address is required.",
                }
            )
        elif _port <= 0:
            set_connection_test_state(
                {
                    "status": "failed",
                    "note": "Port must be a positive integer.",
                }
            )
        else:
            _ok, _err = sdm_test_connection(_ip, _port)
            if _ok:
                set_connection_test_state(
                    {
                        "status": "ok",
                        "note": f"Connected to {_ip}:{_port}.",
                    }
                )
            else:
                set_connection_test_state(
                    {
                        "status": "failed",
                        "note": f"Connection failed: {_err}",
                    }
                )
    return


@app.cell
def _(connection_test_state):
    _state = connection_test_state()
    _status = _state.get("status", "idle")
    _note = _state.get("note", "")
    if _status == "ok":
        connection_status_widget = mo.md(
            f"<span style='color: green; font-weight: 700;'>OK</span>  \n{_note}"
        )
    elif _status == "failed":
        connection_status_widget = mo.md(
            f"<span style='color: red; font-weight: 700;'>Failed</span>  \n{_note}"
        )
    else:
        connection_status_widget = mo.md(_note)
    connection_status_widget
    return (connection_status_widget,)


@app.cell
def _():
    measurement_type_select = mo.ui.dropdown(
        options=["Voltage", "Impedance"],
        value="Voltage",
        label="Measurement Type",
    )
    measurement_type_select
    return (measurement_type_select,)


@app.cell
def _():
    duration_input = mo.ui.number(
        label="Duration (seconds)",
        value=10.0,
        step=0.5,
        start=0.1,
    )
    sampling_interval_input = mo.ui.number(
        label="Sampling Interval (seconds)",
        value=1.0,
        step=0.1,
        start=0.1,
    )
    duration_input, sampling_interval_input
    return duration_input, sampling_interval_input


@app.cell
def _(sampling_interval_input):
    _interval_value = sampling_interval_input.value or 1.0
    if _interval_value <= 0:
        _interval_value = 1.0
    refresh_control = mo.ui.refresh(
        options=[_interval_value],
        default_interval=_interval_value,
        label="Live refresh interval (seconds)",
    )
    refresh_control
    return (refresh_control,)


@app.cell
def _():
    start_measure_button = mo.ui.run_button(label="Start Measurement")
    stop_measure_button = mo.ui.run_button(label="Stop Measurement")
    mo.hstack([start_measure_button, stop_measure_button])
    return start_measure_button, stop_measure_button


@app.cell
def _():
    measurement_state, set_measurement_state = mo.state(
        {
            "running": False,
            "error": "",
            "status": "idle",
            "start_time": None,
            "duration_s": None,
            "interval_s": None,
            "measure_type": None,
            "data": [],
            "last_sample_time": None,
            "client": None,
            "last_query_ms": None,
            "target_samples": None,
        }
    )
    return measurement_state, set_measurement_state


@app.cell
def _(
    duration_input,
    measurement_state,
    measurement_type_select,
    sampling_interval_input,
    sdm_ip_input,
    sdm_port_input,
    sdm_close_client,
    sdm_query_measurement,
    set_measurement_state,
    start_measure_button,
):
    if start_measure_button.value:
        _duration = float(duration_input.value or 0)
        _interval = float(sampling_interval_input.value or 0)
        _ip = (sdm_ip_input.value or "").strip()
        _port = int(sdm_port_input.value or 0)
        _errors = []
        if not _ip:
            _errors.append("IP address is required.")
        if _port <= 0:
            _errors.append("Port must be a positive integer.")
        if _duration <= 0:
            _errors.append("Duration must be greater than 0.")
        if _interval <= 0:
            _errors.append("Sampling interval must be greater than 0.")

        if _errors:
            set_measurement_state(
                {
                    "running": False,
                    "error": " ".join(_errors),
                    "status": "invalid",
                    "start_time": None,
                    "duration_s": None,
                    "interval_s": None,
                    "measure_type": None,
                    "data": [],
                    "last_sample_time": None,
                    "client": None,
                }
            )
        else:
            _client = SDM30xx_SCPI(_ip, _port)
            _start = time.time()
            _data = []
            _target_samples = max(1, math.ceil(_duration / _interval))
            _value, _raw, _unit, _note = sdm_query_measurement(
                _client, measurement_type_select.value
            )
            _elapsed = 0.0
            _timestamp = datetime.fromtimestamp(_start + _elapsed).isoformat(
                timespec="milliseconds"
            )
            if _raw is None and _value is None:
                sdm_close_client(_client)
                set_measurement_state(
                    {
                        "running": False,
                        "error": _note or "No response from SDM30xx on initial query.",
                        "status": "error",
                        "start_time": None,
                        "duration_s": None,
                        "interval_s": None,
                        "measure_type": None,
                        "data": [],
                        "last_sample_time": None,
                        "client": None,
                        "target_samples": None,
                    }
                )
            else:
                _data.append(
                    {
                        "sample": 1,
                        "elapsed_s": round(_elapsed, 3),
                        "timestamp": _timestamp,
                        "value": _value,
                        "unit": _unit,
                        "raw": _raw,
                        "ok": _value is not None,
                        "note": _note,
                    }
                )

                set_measurement_state(
                    {
                        "running": True,
                        "error": "",
                        "status": "running",
                        "start_time": _start,
                        "duration_s": _duration,
                        "interval_s": _interval,
                        "measure_type": measurement_type_select.value,
                        "data": _data,
                        "last_sample_time": _start,
                        "client": _client,
                        "target_samples": _target_samples,
                    }
                )
    return


@app.cell
def _(measurement_state, set_measurement_state, stop_measure_button):
    if stop_measure_button.value:
        _state = measurement_state()
        _client = _state.get("client")
        sdm_close_client(_client)
        set_measurement_state(
            {
                **_state,
                "running": False,
                "status": "stopped",
                "client": None,
            }
        )
    return


@app.cell
def _(measurement_state, refresh_control, sdm_close_client, sdm_query_measurement, set_measurement_state):
    _ = refresh_control.value
    _state = measurement_state()
    mo.stop(not _state.get("running"))

    _client = _state.get("client")
    if _client is None:
        set_measurement_state(
            {
                **_state,
                "running": False,
                "status": "error",
                "error": "No active SDM30xx connection.",
            }
        )
        mo.stop(True)

    _start = _state.get("start_time") or time.time()
    _interval = _state.get("interval_s") or 1.0
    _last = _state.get("last_sample_time")
    _now = time.time()
    _target_samples = _state.get("target_samples")
    _data = list(_state.get("data") or [])

    if _target_samples is not None and len(_data) >= _target_samples:
        sdm_close_client(_client)
        set_measurement_state(
            {
                **_state,
                "running": False,
                "status": "complete",
                "client": None,
            }
        )
        mo.stop(True)

    if _last is None:
        _last = _start

    _remaining = _target_samples - len(_data) if _target_samples is not None else None
    _samples_due = int(max(0.0, _now - _last) // _interval)
    _samples_due = max(1, _samples_due)
    _max_samples_per_tick = 5
    if _remaining is not None:
        _samples_due = min(_samples_due, _remaining)

    _latest_query_ms = None
    for _ in range(min(_samples_due, _max_samples_per_tick)):
        _query_start = time.perf_counter()
        _value, _raw, _unit, _note = sdm_query_measurement(
            _client, _state.get("measure_type") or "Voltage"
        )
        _latest_query_ms = round((time.perf_counter() - _query_start) * 1000.0, 1)
        _last = _last + _interval
        if _raw is None and _value is None:
            sdm_close_client(_client)
            set_measurement_state(
                {
                    **_state,
                    "running": False,
                    "status": "error",
                    "error": _note or "No response from SDM30xx during sampling.",
                    "client": None,
                    "last_query_ms": _latest_query_ms,
                }
            )
            mo.stop(True)

        _elapsed = _last - _start
        _timestamp = datetime.fromtimestamp(_start + _elapsed).isoformat(
            timespec="milliseconds"
        )
        _data.append(
            {
                "sample": len(_data) + 1,
                "elapsed_s": round(_elapsed, 3),
                "timestamp": _timestamp,
                "value": _value,
                "unit": _unit,
                "raw": _raw,
                "ok": _value is not None,
                "note": _note,
            }
        )

    set_measurement_state(
        {
            **_state,
            "data": _data,
            "last_sample_time": _last,
            "last_query_ms": _latest_query_ms or _state.get("last_query_ms"),
        }
    )
    return


@app.cell
def _(measurement_state):
    _state = measurement_state()
    _status = _state.get("status", "idle")
    _error = _state.get("error", "")
    _count = len(_state.get("data") or [])
    _duration = _state.get("duration_s")
    _interval = _state.get("interval_s")
    _last_query_ms = _state.get("last_query_ms")
    _target_samples = _state.get("target_samples")
    _status_lines = [
        f"Status: `{_status}`",
    ]
    if _target_samples is not None:
        _status_lines.append(f"Samples: `{_count}` / `{_target_samples}`")
        _pct = 0.0 if _target_samples == 0 else (_count / _target_samples) * 100.0
        _status_lines.append(f"Progress: `{_pct:.1f}%`")
    else:
        _status_lines.append(f"Samples: `{_count}`")
    if _duration is not None:
        _status_lines.append(f"Duration: `{_duration}` seconds")
    if _interval is not None:
        _status_lines.append(f"Interval: `{_interval}` seconds")
    if _last_query_ms is not None:
        _status_lines.append(f"Last query: `{_last_query_ms} ms`")
    if _error:
        _status_lines.append(f"Error: `{_error}`")
    status_md = mo.md("  \n".join(_status_lines))
    if _target_samples is not None:
        progress_bar = mo.md(
            f"<progress value='{_pct:.1f}' max='100' style='width: 100%;'></progress>"
        )
        status_view = mo.vstack([status_md, progress_bar])
    else:
        status_view = status_md
    status_view


@app.cell
def _(measurement_state, refresh_control):
    _ = refresh_control.value
    _data = measurement_state().get("data") or []
    _x = [row["elapsed_s"] for row in _data if row.get("value") is not None]
    _y = [row["value"] for row in _data if row.get("value") is not None]
    _unit = _data[-1]["unit"] if _data else ""

    if not _x:
        plot_view = mo.md("Plot will appear after the first numeric sample.")
    else:
        mo.md("### Measurement Plot")
        _fig = go.Figure(
            data=[
                go.Scatter(
                    x=_x,
                    y=_y,
                    mode="lines+markers",
                )
            ]
        )
        _fig.update_layout(
            title="Measurement vs Time",
            xaxis_title="Elapsed (s)",
            yaxis_title=f"Value ({_unit})" if _unit else "Value",
            margin=dict(l=40, r=20, t=40, b=40),
            height=360,
        )
        plot_view = mo.ui.plotly(_fig)
    plot_view


@app.cell
def _(measurement_state, refresh_control):
    _ = refresh_control.value
    _data = measurement_state().get("data") or []
    if not _data:
        table_view = mo.md("No samples yet.")
    else:
        table_view = mo.ui.table(
            _data,
            page_size=25,
            label="Live Samples",
            show_download=False,
        )
    table_view


if __name__ == "__main__":
    app.run()
