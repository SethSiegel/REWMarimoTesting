import asyncio
import json
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from lea_monitor import LEAMonitor
import threading


app = Flask(__name__)
app.config['SECRET_KEY'] = 'lea-limit-tester-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

monitor: LEAMonitor = None
event_loop = None
loop_thread = None



def run_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def init_event_loop():
    global event_loop, loop_thread
    event_loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=run_event_loop, args=(event_loop,), daemon=True)
    loop_thread.start()


async def socketio_callback(data_type: str, data):
    if data_type == "channel_count":
        print(f"Detected {data['count']} channels: {data['channels']}", flush=True)
    socketio.emit(data_type, data)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check_filename', methods=['POST'])
def check_filename():
    data = request.json
    filename = data.get('filename', '')

    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

    file_path = logs_dir / filename
    exists = file_path.exists()

    return jsonify({'exists': exists, 'filename': filename})


@socketio.on('connect')
def handle_socketio_connect():
    print(f"Socket.IO client connected: {request.sid}", flush=True)


@socketio.on('disconnect')
def handle_socketio_disconnect():
    print(f"Socket.IO client disconnected: {request.sid}", flush=True)


@socketio.on('connect_amp')
def handle_connect(data):
    global monitor

    amp_address = data.get('address', 'ws://192.168.1.100:1234')

    print(f"Connecting to LEA at: {amp_address}", flush=True)

    if monitor is not None:
        try:
            future = asyncio.run_coroutine_threadsafe(monitor.disconnect(), event_loop)
            future.result(timeout=5)
        except Exception as e:
            print(f"Error disconnecting monitor: {e}", flush=True)
        monitor = None
        time.sleep(0.5)

    monitor = LEAMonitor(amp_address)
    monitor.register_callback(socketio_callback)

    try:
        future = asyncio.run_coroutine_threadsafe(monitor.connect(), event_loop)
        success = future.result(timeout=10)
    except Exception as e:
        print(f"Error connecting: {e}", flush=True)
        success = False

    if success:
        receive_future = asyncio.run_coroutine_threadsafe(monitor.receive_loop(), event_loop)
        print(f"Connected successfully", flush=True)
        socketio.emit('connection_status', {
            'connected': True,
            'address': amp_address
        }, room=request.sid)
    else:
        error_msg = "Failed to connect to amplifier. Check IP address and ensure amplifier is powered on."
        socketio.emit('connection_status', {
            'connected': False,
            'address': amp_address,
            'error': error_msg
        }, room=request.sid)

    return {'status': 'ok', 'connected': success}


@socketio.on('disconnect_amp')
def handle_disconnect():
    global monitor

    if monitor:
        future = asyncio.run_coroutine_threadsafe(monitor.disconnect(), event_loop)
        future.result(timeout=5)
        monitor = None

    emit('connection_status', {'connected': False})


@socketio.on('set_signal_generator')
def handle_set_signal_generator(data):
    if not monitor or not monitor.connected:
        emit('signal_generator_set', {'success': False, 'error': 'Not connected to amplifier'})
        return

    signal_type = data.get('type', 'off')
    frequency = data.get('frequency')

    try:
        future = asyncio.run_coroutine_threadsafe(
            monitor.set_signal_generator(signal_type, frequency),
            event_loop
        )
        success = future.result(timeout=10)
    except Exception as e:
        print(f"Error setting signal generator: {e}", flush=True)
        success = False

    emit('signal_generator_set', {
        'success': success,
        'type': signal_type,
        'frequency': frequency
    })


@socketio.on('enable_channel_generator')
def handle_enable_channel_generator(data):
    if not monitor or not monitor.connected:
        emit('error', {'message': 'Not connected to amplifier'})
        return

    channel = data.get('channel', 1)
    enabled = data.get('enabled', False)
    fader = data.get('fader', 0.0)

    future = asyncio.run_coroutine_threadsafe(
        monitor.enable_signal_generator(channel, enabled, fader),
        event_loop
    )
    success = future.result(timeout=5)

    emit('channel_generator_enabled', {
        'success': success,
        'channel': channel,
        'enabled': enabled,
        'fader': fader
    })


@socketio.on('set_output_gain')
def handle_set_output_gain(data):
    if not monitor or not monitor.connected:
        emit('error', {'message': 'Not connected to amplifier'})
        return

    channel = data.get('channel', 1)
    fader = data.get('fader', 0.0)
    mute = data.get('mute', False)

    future = asyncio.run_coroutine_threadsafe(
        monitor.set_output_gain(channel, fader, mute),
        event_loop
    )
    success = future.result(timeout=5)

    emit('output_gain_set', {
        'success': success,
        'channel': channel,
        'fader': fader,
        'mute': mute
    })


@socketio.on('start_logging')
def handle_start_logging(data=None):
    if not monitor:
        emit('error', {'message': 'Not connected to amplifier'})
        return

    filename = None
    if data and isinstance(data, dict):
        filename = data.get('filename')

    future = asyncio.run_coroutine_threadsafe(
        monitor.start_logging(filename=filename),
        event_loop
    )
    future.result(timeout=5)
    emit('logging_status', {
        'active': True,
        'path': str(monitor.csv_path)
    })


@socketio.on('stop_logging')
def handle_stop_logging():
    if not monitor:
        return

    future = asyncio.run_coroutine_threadsafe(
        monitor.stop_logging(),
        event_loop
    )
    future.result(timeout=5)
    emit('logging_status', {'active': False})


@socketio.on('get_device_info')
def handle_get_device_info():
    if not monitor or not monitor.connected:
        emit('error', {'message': 'Not connected to amplifier'})
        return

    future = asyncio.run_coroutine_threadsafe(
        monitor.get_device_info(),
        event_loop
    )
    future.result(timeout=5)


@socketio.on('get_latest_data')
def handle_get_latest_data():
    if not monitor:
        emit('latest_data', {})
        return

    data = monitor.get_latest_data()
    emit('latest_data', data)




if __name__ == '__main__':
    init_event_loop()
    print("=" * 40)
    print("  ResonX Limit Tester Server")
    print("=" * 40)
    print("Open http://localhost:5000 in your browser")
    print()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
