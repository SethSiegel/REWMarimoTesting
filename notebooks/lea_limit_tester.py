# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.11",
#     "plotly>=5.22.0",
#     "websockets>=12.0",
# ]
# [tool.marimo.opengraph]
# title = "LEA Limit Tester"
# description = "Marimo dashboard for the ResonX LEA limit tester controls and logging."
# image = "https://www.tpimagazine.com/wp-content/uploads/2019/01/LEA_Logo_Black.png"
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(app_title="LEA Limit Tester")


with app.setup:
    import sys
    import time
    import asyncio
    import threading
    from pathlib import Path
    import marimo as mo
    import plotly.graph_objects as go

    repo_root = Path(__file__).resolve().parents[1]
    limit_root = repo_root / "vibe_bullshit" / "resonx-limit-tester-main"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(limit_root) not in sys.path:
        sys.path.insert(0, str(limit_root))

    from lea_monitor import LEAMonitor


@app.cell
def _():
    def lt_create_event_loop():
        _loop = asyncio.new_event_loop()

        def _runner():
            asyncio.set_event_loop(_loop)
            _loop.run_forever()

        _thread = threading.Thread(target=_runner, daemon=True)
        _thread.start()
        return _loop, _thread

    def lt_submit(loop, coro, timeout=10.0):
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    return lt_create_event_loop, lt_submit


@app.cell
def _():
    mo.md(
        r"""
        # LEA Limit Tester
        ---
        Control LEA signal generator + channel gains and log limit-test data to CSV.
        """
    )
    return


@app.cell
def _():
    amp_address_input = mo.ui.text(
        label="LEA WebSocket Address",
        value="ws://192.168.1.100:1234",
        full_width=True,
    )
    amp_address_input
    return (amp_address_input,)


@app.cell
def _():
    connect_button = mo.ui.run_button(label="Connect")
    disconnect_button = mo.ui.run_button(label="Disconnect")
    mo.hstack([connect_button, disconnect_button])
    return connect_button, disconnect_button


@app.cell
def _():
    loop_state, set_loop_state = mo.state({"loop": None, "thread": None})
    return loop_state, set_loop_state


@app.cell
def _():
    limit_state, set_limit_state = mo.state(
        {
            "monitor": None,
            "connected": False,
            "amp_address": "",
            "error": "",
            "logging_active": False,
            "log_path": "",
        }
    )
    return limit_state, set_limit_state


@app.cell
def _(amp_address_input, connect_button, limit_state, lt_create_event_loop, lt_submit, loop_state, set_limit_state, set_loop_state):
    if connect_button.value:
        _amp_address = (amp_address_input.value or "").strip()
        if not _amp_address:
            set_limit_state(
                {
                    **limit_state(),
                    "connected": False,
                    "error": "LEA WebSocket address is required.",
                }
            )
        else:
            _loop_info = loop_state()
            _loop = _loop_info.get("loop")
            _thread = _loop_info.get("thread")
            if _loop is None or _loop.is_closed():
                _loop, _thread = lt_create_event_loop()
                set_loop_state({"loop": _loop, "thread": _thread})

            _current = limit_state()
            _monitor_existing = _current.get("monitor")
            if _monitor_existing is not None:
                try:
                    lt_submit(_loop, _monitor_existing.disconnect(), timeout=5.0)
                except Exception:
                    pass

            _logs_dir = (Path(__file__).resolve().parents[1]
                         / "vibe_bullshit"
                         / "resonx-limit-tester-main"
                         / "logs")
            _logs_dir.mkdir(exist_ok=True)

            _monitor = LEAMonitor(_amp_address, output_dir=str(_logs_dir))
            _success = False
            _error = ""
            try:
                _success = bool(lt_submit(_loop, _monitor.connect(), timeout=10.0))
            except Exception as _exc:
                _success = False
                _error = str(_exc)

            if _success:
                try:
                    asyncio.run_coroutine_threadsafe(_monitor.receive_loop(), _loop)
                except Exception as _exc:
                    _error = str(_exc)

            set_limit_state(
                {
                    **limit_state(),
                    "monitor": _monitor if _success else None,
                    "connected": _success,
                    "amp_address": _amp_address,
                    "error": "" if _success else (_error or "Failed to connect."),
                }
            )
    return


@app.cell
def _(disconnect_button, limit_state, lt_submit, loop_state, set_limit_state):
    if disconnect_button.value:
        _state = limit_state()
        _monitor = _state.get("monitor")
        _loop = loop_state().get("loop")
        if _monitor is not None and _loop is not None:
            try:
                lt_submit(_loop, _monitor.disconnect(), timeout=5.0)
            except Exception:
                pass
        set_limit_state(
            {
                **_state,
                "monitor": None,
                "connected": False,
                "error": "",
                "logging_active": False,
                "log_path": "",
            }
        )
    return


@app.cell
def _(limit_state):
    _state = limit_state()
    _connected = _state.get("connected")
    _address = _state.get("amp_address") or "-"
    _error = _state.get("error") or ""
    if _connected:
        status_widget = mo.md(
            f"<span style='color: green; font-weight: 700;'>Connected</span>  \n{_address}"
        )
    else:
        note = _error if _error else "Not connected."
        status_widget = mo.md(
            f"<span style='color: red; font-weight: 700;'>Disconnected</span>  \n{note}"
        )
    status_widget
    return (status_widget,)


@app.cell
def _():
    mo.md(
        r"""
        ## Signal Generator
        """
    )
    return


@app.cell
def _():
    signal_type_select = mo.ui.dropdown(
        options=["off", "Tone", "Pink Noise", "White Noise"],
        value="Tone",
        label="Signal Type",
    )
    signal_frequency_input = mo.ui.number(
        label="Frequency (Hz)",
        value=1000.0,
        start=20.0,
        stop=20000.0,
        step=10.0,
        full_width=True,
    )
    set_signal_button = mo.ui.run_button(label="Set Signal Generator")
    mo.hstack([signal_type_select, signal_frequency_input, set_signal_button])
    return signal_frequency_input, signal_type_select, set_signal_button


@app.cell
def _(limit_state, lt_submit, loop_state, set_signal_button, signal_frequency_input, signal_type_select):
    if set_signal_button.value:
        _state = limit_state()
        _monitor = _state.get("monitor")
        _loop = loop_state().get("loop")
        mo.stop(_monitor is None or _loop is None or not _state.get("connected"))
        _signal_type = signal_type_select.value or "off"
        _frequency = float(signal_frequency_input.value or 0) or None
        if _signal_type == "off":
            _frequency = None
        try:
            lt_submit(_loop, _monitor.set_signal_generator(_signal_type, _frequency), timeout=8.0)
        except Exception:
            pass
    return


@app.cell
def _():
    mo.md(
        r"""
        ## Channel Controls
        """
    )
    return


@app.cell
def _(channel_ui_defaults_state):
    _defaults = channel_ui_defaults_state()
    channel_select = mo.ui.dropdown(
        options=[str(ch) for ch in range(1, 9)],
        value="1",
        label="Channel",
    )
    output_gain_slider = mo.ui.number(
        label="Output Gain (dB)",
        value=_defaults.get("output_gain", -40.0),
        start=-60.0,
        stop=0.0,
        step=0.5,
    )
    output_mute_checkbox = mo.ui.checkbox(
        label="Mute Output",
        value=bool(_defaults.get("output_mute", False)),
    )
    set_output_gain_button = mo.ui.run_button(label="Set Output Gain")

    generator_fader_slider = mo.ui.number(
        label="Generator Fader (dB)",
        value=_defaults.get("generator_fader", -40.0),
        start=-60.0,
        stop=0.0,
        step=0.5,
    )
    generator_enable_checkbox = mo.ui.checkbox(
        label="Enable Generator",
        value=bool(_defaults.get("generator_enabled", False)),
    )
    set_generator_button = mo.ui.run_button(label="Set Generator Fader")
    arm_channel_button = mo.ui.run_button(label="Arm Channel (One-Click)")

    mo.hstack([channel_select, output_gain_slider, output_mute_checkbox, set_output_gain_button])
    mo.hstack([generator_fader_slider, generator_enable_checkbox, set_generator_button])
    arm_channel_button
    return (
        arm_channel_button,
        channel_select,
        generator_enable_checkbox,
        generator_fader_slider,
        output_gain_slider,
        output_mute_checkbox,
        set_generator_button,
        set_output_gain_button,
    )


@app.cell
def _():
    channel_ui_defaults_state, set_channel_ui_defaults_state = mo.state(
        {
            "output_gain": -40.0,
            "output_mute": False,
            "generator_fader": -40.0,
            "generator_enabled": False,
        }
    )
    return channel_ui_defaults_state, set_channel_ui_defaults_state


@app.cell
def _():
    arm_status_state, set_arm_status_state = mo.state(
        {
            "status": "idle",
            "note": "Click Arm Channel to auto-enable signal and output.",
        }
    )
    return arm_status_state, set_arm_status_state


@app.cell
def _(
    arm_channel_button,
    channel_select,
    generator_enable_checkbox,
    generator_fader_slider,
    limit_state,
    lt_submit,
    loop_state,
    output_gain_slider,
    output_mute_checkbox,
    set_generator_button,
    set_output_gain_button,
    set_arm_status_state,
    set_channel_ui_defaults_state,
    signal_frequency_input,
    signal_type_select,
):
    _state = limit_state()
    _monitor = _state.get("monitor")
    _loop = loop_state().get("loop")
    mo.stop(_monitor is None or _loop is None or not _state.get("connected"))

    _channel = int(channel_select.value or 1)

    if set_output_gain_button.value:
        _gain = float(output_gain_slider.value or -60.0)
        _mute = bool(output_mute_checkbox.value)
        try:
            lt_submit(_loop, _monitor.set_output_gain(_channel, _gain, _mute), timeout=5.0)
        except Exception:
            pass

    if set_generator_button.value:
        _fader = float(generator_fader_slider.value or -60.0)
        _enabled = bool(generator_enable_checkbox.value)
        try:
            lt_submit(_loop, _monitor.enable_signal_generator(_channel, _enabled, _fader), timeout=5.0)
        except Exception:
            pass

    if arm_channel_button.value:
        _signal_type = signal_type_select.value or "off"
        _frequency = float(signal_frequency_input.value or 0) or None
        if _signal_type == "off":
            _frequency = None
        _fader = float(generator_fader_slider.value or -60.0)
        _gain = float(output_gain_slider.value or -60.0)
        _arm_errors = []
        _sig_ok = None
        _gen_ok = None
        _out_ok = None

        try:
            _sig_ok = lt_submit(
                _loop,
                _monitor.set_signal_generator(_signal_type, _frequency),
                timeout=8.0,
            )
        except Exception as _exc:
            _arm_errors.append(f"Signal generator: {_exc}")

        try:
            _gen_ok = lt_submit(
                _loop,
                _monitor.enable_signal_generator(_channel, True, _fader),
                timeout=5.0,
            )
        except Exception as _exc:
            _arm_errors.append(f"Generator enable: {_exc}")

        try:
            _out_ok = lt_submit(
                _loop,
                _monitor.set_output_gain(_channel, _gain, False),
                timeout=5.0,
            )
        except Exception as _exc:
            _arm_errors.append(f"Output gain: {_exc}")

        set_channel_ui_defaults_state(
            {
                "output_gain": _gain,
                "output_mute": False,
                "generator_fader": _fader,
                "generator_enabled": True,
            }
        )

        if _arm_errors or _sig_ok is False or _gen_ok is False or _out_ok is False:
            _note = " ; ".join(_arm_errors) if _arm_errors else "One or more commands failed."
            set_arm_status_state(
                {
                    "status": "error",
                    "note": _note,
                }
            )
        else:
            set_arm_status_state(
                {
                    "status": "ok",
                    "note": (
                        f"Armed channel {_channel}: {_signal_type} "
                        f"{'' if _frequency is None else f'@ {_frequency:.0f} Hz'}, "
                        f"gen fader {_fader:.1f} dB, output gain {_gain:.1f} dB."
                    ),
                }
            )
    return


@app.cell
def _(arm_status_state):
    _state = arm_status_state()
    _status = _state.get("status", "idle")
    _note = _state.get("note", "")
    if _status == "ok":
        arm_status_widget = mo.md(
            f"<span style='color: green; font-weight: 700;'>Armed</span>  \n{_note}"
        )
    elif _status == "error":
        arm_status_widget = mo.md(
            f"<span style='color: red; font-weight: 700;'>Arm Failed</span>  \n{_note}"
        )
    else:
        arm_status_widget = mo.md(_note)
    arm_status_widget
    return (arm_status_widget,)


@app.cell
def _():
    mo.md(
        r"""
        ## Logging
        """
    )
    return


@app.cell
def _():
    log_filename_input = mo.ui.text(
        label="Log filename (optional)",
        placeholder="lea_test_YYYYMMDD_HHMMSS.csv",
        full_width=True,
    )
    start_logging_button = mo.ui.run_button(label="Start Logging")
    stop_logging_button = mo.ui.run_button(label="Stop Logging")
    mo.hstack([start_logging_button, stop_logging_button])
    return log_filename_input, start_logging_button, stop_logging_button


@app.cell
def _(limit_state, log_filename_input, lt_submit, loop_state, set_limit_state, start_logging_button, stop_logging_button):
    _state = limit_state()
    _monitor = _state.get("monitor")
    _loop = loop_state().get("loop")
    mo.stop(_monitor is None or _loop is None or not _state.get("connected"))

    if start_logging_button.value:
        _name = (log_filename_input.value or "").strip() or None
        try:
            lt_submit(_loop, _monitor.start_logging(filename=_name), timeout=5.0)
            set_limit_state(
                {
                    **_state,
                    "logging_active": True,
                    "log_path": str(_monitor.csv_path) if _monitor.csv_path else "",
                }
            )
        except Exception:
            pass

    if stop_logging_button.value:
        try:
            lt_submit(_loop, _monitor.stop_logging(), timeout=5.0)
        except Exception:
            pass
        set_limit_state(
            {
                **_state,
                "logging_active": False,
            }
        )
    return


@app.cell
def _(limit_state):
    _state = limit_state()
    _active = _state.get("logging_active")
    _path = _state.get("log_path") or "-"
    if _active:
        mo.md(f"<span style='color: green; font-weight: 700;'>Logging</span>  \n{_path}")
    else:
        mo.md("Logging is idle.")
    return


@app.cell
def _():
    refresh_control = mo.ui.refresh(
        options=["0.5s", "1s", "2s"],
        default_interval="1s",
        label="Live data refresh",
    )
    refresh_control
    return (refresh_control,)


@app.cell
def _():
    history_state, set_history_state = mo.state(
        {
            "start_time": None,
            "timestamps": [],
            "voltage": {str(ch): [] for ch in range(1, 9)},
            "current": {str(ch): [] for ch in range(1, 9)},
            "power": {str(ch): [] for ch in range(1, 9)},
            "impedance": {str(ch): [] for ch in range(1, 9)},
        }
    )
    return history_state, set_history_state


@app.cell
def _(history_state, limit_state, refresh_control, set_history_state):
    _ = refresh_control.value
    _state = limit_state()
    _monitor = _state.get("monitor")
    mo.stop(_monitor is None or not _state.get("connected"))
    latest_data = _monitor.get_latest_data()

    _history = history_state()
    _now = time.time()
    _start_time = _history.get("start_time")
    if _start_time is None:
        _start_time = _now

    _max_points = 300

    def _copy_metric(_metric_dict):
        return {k: list(v) for k, v in (_metric_dict or {}).items()}

    _new_history = {
        "start_time": _start_time,
        "timestamps": list(_history.get("timestamps", [])),
        "voltage": _copy_metric(_history.get("voltage")),
        "current": _copy_metric(_history.get("current")),
        "power": _copy_metric(_history.get("power")),
        "impedance": _copy_metric(_history.get("impedance")),
    }

    _new_history["timestamps"].append(_now)
    if len(_new_history["timestamps"]) > _max_points:
        _new_history["timestamps"] = _new_history["timestamps"][-_max_points:]

    def _append_metric(_metric_map, _channel, _value):
        if _value is None:
            return
        try:
            _val = float(_value)
        except (TypeError, ValueError):
            return
        _series = _metric_map.setdefault(_channel, [])
        _series.append((_now, _val))
        if len(_series) > _max_points:
            _metric_map[_channel] = _series[-_max_points:]

    _voltage = latest_data.get("voltage", {})
    _current = latest_data.get("current", {})
    _power = latest_data.get("power", {})
    _impedance = latest_data.get("impedance", {})

    for _ch in range(1, 9):
        _ch_str = str(_ch)
        _append_metric(_new_history["voltage"], _ch_str, _voltage.get(_ch_str))
        _append_metric(_new_history["current"], _ch_str, _current.get(_ch_str))
        _append_metric(_new_history["power"], _ch_str, _power.get(_ch_str))
        _append_metric(
            _new_history["impedance"],
            _ch_str,
            _impedance.get(_ch_str, {}).get("measuredImpedance"),
        )

    set_history_state(_new_history)
    return (latest_data,)


@app.cell
def _(latest_data):
    mo.md("## Latest Channel Data")
    _rows = []
    _levels = latest_data.get("levels", {})
    _voltage = latest_data.get("voltage", {})
    _current = latest_data.get("current", {})
    _power = latest_data.get("power", {})
    _impedance = latest_data.get("impedance", {})
    _status = latest_data.get("status", {})

    for _ch in range(1, 9):
        _ch_str = str(_ch)
        _rows.append(
            {
                "channel": _ch,
                "level_db": _levels.get(_ch_str, {}).get("level_db"),
                "voltage": _voltage.get(_ch_str),
                "current": _current.get(_ch_str),
                "power": _power.get(_ch_str),
                "impedance": _impedance.get(_ch_str, {}).get("measuredImpedance"),
                "thermal": _status.get(_ch_str, {}).get("thermal"),
                "fault": _status.get(_ch_str, {}).get("fault"),
                "clip": _status.get(_ch_str, {}).get("clip"),
                "limiting": _status.get(_ch_str, {}).get("limiting"),
            }
        )

    mo.ui.table(_rows, page_size=8, show_download=False)
    return


@app.cell
def _(history_state):
    mo.md("## Live Charts")
    _history = history_state()
    _start_time = _history.get("start_time")
    mo.stop(_start_time is None, mo.md("No live plot data yet."))

    def _build_fig(_metric_key, _title, _y_label):
        _fig = go.Figure()
        _metric = _history.get(_metric_key, {})
        for _ch in range(1, 9):
            _ch_str = str(_ch)
            _series = _metric.get(_ch_str, [])
            if not _series:
                continue
            _x = [pt[0] - _start_time for pt in _series]
            _y = [pt[1] for pt in _series]
            _fig.add_trace(
                go.Scatter(
                    x=_x,
                    y=_y,
                    mode="lines",
                    name=f"Ch {_ch}",
                )
            )
        _fig.update_layout(
            title=_title,
            xaxis_title="Elapsed (s)",
            yaxis_title=_y_label,
            height=280,
            margin=dict(l=40, r=20, t=70, b=50),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.08,
                xanchor="left",
                x=0,
            ),
        )
        return _fig

    _voltage_fig = _build_fig("voltage", "Voltage", "Volts (V)")
    _current_fig = _build_fig("current", "Current", "Amps (A)")
    _power_fig = _build_fig("power", "Power", "Watts (W)")
    _impedance_fig = _build_fig("impedance", "Impedance", "Ohms (Ω)")

    mo.vstack(
        [
            mo.ui.plotly(_voltage_fig),
            mo.ui.plotly(_current_fig),
            mo.ui.plotly(_power_fig),
            mo.ui.plotly(_impedance_fig),
        ]
    )
    return


@app.cell
def _(latest_data):
    mo.md("## Power Supply")
    _ps = latest_data.get("power_supply", {})
    mo.stop(not _ps, mo.md("No power supply data yet."))
    _ps_rows = [{"metric": k, "value": v} for k, v in _ps.items()]
    mo.ui.table(_ps_rows, page_size=12, show_download=False)
    return


if __name__ == "__main__":
    app.run()
