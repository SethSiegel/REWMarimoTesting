# ResonX Limit Tester

A testing and monitoring tool for ResonX (LEA) amplifiers that helps determine safe operating power limits while logging performance metrics over time.

## Features

- **Real-time Monitoring**: Track voltage, current, power, and load impedance across all channels
- **Signal Generation Control**: Control LEA's built-in signal generator (tones, pink noise, white noise)
- **Live Parameter Updates**: All signal changes (frequency, type, gain) update in real-time without toggling
- **CSV Data Logging**: Log all measurements with timestamps for analysis
- **Real-time Graphs**: Live charts showing voltage, current, power, and impedance trends
- **Stubbed Mode**: Test all features without physical hardware using realistic simulated data

## Prerequisites

- Python 3.11 or higher
- LEA amplifier with WebSocket API access (typically port 1234)
- Network connectivity to the amplifier

## Installation

1. Navigate to the limit-tester directory:
```bash
cd limit-tester
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Connection Modes

The application supports two connection modes that can be toggled directly in the UI:

#### Stubbed Data Mode (Default)
Use this mode for **testing without a physical amplifier**:
- Check "Use Stubbed Data" checkbox in the Connection panel
- Test all features without hardware
- Realistic, varying data that simulates actual amplifier behavior
- Signal wobble and natural variations
- Responds to signal generator settings (frequency, type, gain)
- Shows status flags (clip, limiting, thermal) at appropriate power levels
- Safe for developing and testing new features

#### Real Hardware Mode
Use this mode to **connect to an actual LEA amplifier**:
- Uncheck "Use Stubbed Data" checkbox in the Connection panel
- Enter the amplifier's actual WebSocket address
- Click "Connect"
- Requires amplifier to be powered on and network accessible

**Switching modes:** Simply check or uncheck the "Use Stubbed Data" checkbox before connecting. You can switch modes by disconnecting and reconnecting with a different mode selected.

### Starting the Server

1. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Run the server:
```bash
./run.sh
```

Or manually:
```bash
python3 server.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

### Connecting to an Amplifier

1. In the **Connection** section:
   - **For testing:** Check "Use Stubbed Data" (default) - no hardware needed
   - **For real hardware:** Uncheck "Use Stubbed Data" and enter your amplifier's WebSocket address
     - Default format: `ws://192.168.1.100:1234`
     - Replace `192.168.1.100` with your amplifier's IP address

2. Click **Connect**

3. Wait for the connection status indicator to turn green

4. The server console will show whether you connected in STUB MODE or REAL HARDWARE mode

### Manual Control

Use this mode to manually test specific frequencies and power levels:

1. **Set Signal Type**: Choose tone (sine wave), pink noise, or white noise
2. **Set Frequency**: Enter the test frequency in Hz (20-20000)
3. **Select Test Channel**: Choose which amplifier channel to test
4. **Adjust Output Gain**: Use the slider to set power level (-60 to 0 dB)
5. **Enable Generator**: Click to start signal output
6. **Real-time Updates**: Once enabled, all changes update automatically:
   - **Frequency changes**: Adjusting the frequency slider instantly changes the tone/signal
   - **Signal type changes**: Switching between tone, pink noise, and white noise takes effect immediately
   - **Gain changes**: Moving the gain slider updates power level in real-time
7. **Monitor**: Watch voltage, current, power, and impedance update live as you adjust settings
8. **Disable Generator**: Click "Disable Generator" to stop signal output when done

**Pro Tip**: You can smoothly sweep through frequencies or power levels by dragging the sliders and watch the amplifier's response in real-time on the charts!


### Data Logging

All measurements can be logged to CSV for later analysis:

1. Click **Start Logging** before or during testing
2. The log file path will be displayed (saved in `logs/` directory)
3. Click **Stop Logging** when finished

#### Recording Strategy

CSV rows are written at a fixed 100ms interval (10 rows/second) regardless of whether new data arrived from the LEA. This decouples recording from the LEA's notification timing and ensures continuous, gap-free data.

Each row includes a `data_source` column:
- **`live`**: At least one new LEA notification arrived since the previous row. Values reflect fresh hardware measurements.
- **`fill`**: No new notification arrived in this 100ms window. Values are carried forward from the most recent measurement.

Per-field staleness (2-second timeout):
- **Fresh** (last LEA update < 2s ago): The actual received value is recorded.
- **Stale** (last LEA update > 2s ago): The value is zeroed out, indicating the LEA stopped reporting this field.
- **Never received** (LEA has never sent this field for this channel): Recorded as empty, distinguishable from a true zero.

This means in the CSV:
- A numeric value = the LEA reported this within the last 2 seconds
- `0` = the LEA stopped reporting this field more than 2 seconds ago
- Empty cell = the LEA has never reported this field for this channel

#### Impedance Source

Impedance values come exclusively from the LEA's own `measuredImpedance` field via the `/amp/channels/{N}/loadMonitor` subscription. There is no frontend voltage/current calculation -- the hardware measurement is the authoritative source.

#### LEA Notification Behavior

The LEA does not send all fields in every notification. Voltage, current, dB level, impedance, and status flags may arrive in separate notifications at different rates. Some fields (like `level_amps`) may not be sent at all under certain drive conditions. The recording strategy accounts for this by carrying forward the last known value and tracking staleness independently per field per channel.

### Real-time Monitoring

The monitoring panel shows:

- **Channel Cards**: Current voltage, current, power, and impedance for channels 1-2
- **Live Charts**: Four real-time graphs showing:
  - **Impedance Chart**: Load impedance (Ω) over time
  - **Voltage Chart**: Output voltage (V) over time
  - **Current Chart**: Output current (A) over time
  - **Power Chart**: Output power (W) over time
- Charts automatically update as signal parameters change
- Data points are throttled to 100ms intervals for smooth performance

## Safety Considerations

**IMPORTANT**: This tool is designed to test hardware limits. Use with caution:

1. **Start Conservative**: Begin with low power levels (-40 dB) and increase gradually
2. **Monitor Metrics**: Watch voltage, current, power, and impedance readings
3. **Have Proper Loads**: Ensure appropriate loads are connected to test channels
4. **Ventilation**: Ensure adequate cooling/ventilation for the amplifier
5. **Know Your Limits**: Understand your amplifier's rated specifications before testing
6. **Use Stub Mode First**: Test your workflow in stub mode before connecting to real hardware

## Understanding the Data

### Voltage (V)
- RMS output voltage from the amplifier
- Increases with gain level
- Should remain stable at a given power setting

### Current (A)
- RMS output current to the load
- Depends on both voltage and load impedance (I = V / Z)
- Higher current with lower impedance loads

### Power (W)
- Real power delivered to the load (P = V × I)
- Key metric for determining amplifier limits
- Watch for thermal issues at sustained high power

### Impedance (Ω)
- Load impedance as measured by the amplifier
- Should remain relatively stable during testing
- Significant changes may indicate load issues or connection problems

## Output Files

CSV log files are saved in the `logs/` directory with format:
```
lea_test_YYYYMMDD_HHMMSS.csv
```

Columns include:
- `timestamp`: ISO format timestamp with millisecond precision
- `frequency`: Test frequency in Hz
- `signal_type`: Tone/Pink Noise/White Noise/off
- `data_source`: `live` (fresh LEA data) or `fill` (carried forward, no new notification)
- `ps_*`: Power supply fields (acLineVoltage, acLineCurrent, acLineWatts, fault, thermal, etc.)
- `ch{N}_output_fader`: Channel N output fader level (dB)
- `ch{N}_generator_fader`: Channel N signal generator fader level (dB)
- `ch{N}_level_db`: Channel N output level (dB)
- `ch{N}_voltage`: Channel N RMS voltage (V)
- `ch{N}_current`: Channel N RMS current (A)
- `ch{N}_power`: Channel N power output (W), calculated as voltage * current
- `ch{N}_impedance`: Channel N load impedance from LEA hardware measurement (not calculated)
- `ch{N}_thermal`: Channel N thermal flag (0/1)
- `ch{N}_fault`: Channel N fault flag (0/1)
- `ch{N}_clip`: Channel N clip flag (0/1)
- `ch{N}_limiting`: Channel N limiting flag (0/1)

Empty cells indicate the LEA has never reported that field. A value of `0` in a field that was previously non-empty indicates the LEA stopped reporting it (staleness timeout of 2 seconds).

## Troubleshooting

### Cannot Connect to Amplifier
- Verify the IP address is correct
- Ensure the amplifier is powered on and network accessible
- Check that port 1234 is not blocked by firewall
- Try pinging the amplifier IP address

### No Data Updates
- Check that you've enabled the signal generator on a channel
- Verify the channel has an appropriate load connected
- Try disconnecting and reconnecting

### CSV File Not Created
- Ensure you clicked "Start Logging" before testing
- Check that the `logs/` directory exists and is writable
- Look for error messages in the server console

### Server Won't Start
- Check that port 5000 is not already in use
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Try using a different port by editing `server.py` (change `port=5000`)

## Technical Details

### Architecture

```
┌─────────────────────┐
│   Web Browser       │
│   (HTML/JS/Charts)  │
└──────────┬──────────┘
           │ Socket.IO
           │ HTTP
┌──────────▼──────────┐
│   Flask Server      │
│   (Python)          │
└──────────┬──────────┘
           │ WebSocket
           │ LEA API
┌──────────▼──────────┐
│   LEA Amplifier     │
│   (port 1234)       │
└─────────────────────┘
```

### LEA WebSocket API

Messages use the format:
```json
{
    "leaApi": "1.0",
    "url": "/amp/channels/1/levels",
    "method": "get",
    "id": 1
}
```

Key endpoints:
- `/amp/signalGenerator` - Control signal generation
- `/amp/channels/{N}/levels` - Read output levels
- `/amp/channels/{N}/loadMonitor` - Read impedance
- `/amp/channels/{N}/inputSelector` - Enable/disable signal generator
- `/amp/channels/{N}/output` - Control output gain and mute

## Development

### Project Structure
```
limit-tester/
├── lea_monitor.py          # LEA WebSocket client (real hardware)
├── lea_monitor_stub.py     # LEA simulator (stubbed data)
├── server.py               # Flask server with Socket.IO
├── run.sh                  # Startup script
├── templates/
│   └── index.html          # Web interface
├── static/
│   ├── css/
│   │   └── style.css       # Styles
│   ├── js/
│   │   └── app.js          # Frontend logic
│   └── fonts/
│       └── transducer.otf  # Custom font
├── logs/                   # CSV output directory
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Extending the Tool

To add new features:

1. **New LEA Commands**: Add methods to `LEAMonitor` class in `lea_monitor.py`
2. **Server Endpoints**: Add Socket.IO handlers in `server.py`
3. **UI Controls**: Update `templates/index.html` and `static/js/app.js`
4. **Logging Fields**: Modify `start_logging()` and `log_to_csv()` in `lea_monitor.py`

## License

This tool is part of the ESR Venue Controls project.

## Support

For issues or questions, please refer to the main ESR project documentation or contact your system administrator.
