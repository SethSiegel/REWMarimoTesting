Chart.register(
    Chart.LineController,
    Chart.LineElement,
    Chart.PointElement,
    Chart.LinearScale,
    Chart.TimeScale,
    Chart.Title,
    Chart.Legend,
    Chart.Tooltip,
    Chart.Filler,
    Chart.CategoryScale
);

console.log('Chart.js version:', Chart.version);
console.log('Chart.js registered controllers:', Object.keys(Chart.registry.controllers));
console.log('Chart.js registered scales:', Object.keys(Chart.registry.scales));
console.log('Luxon available:', typeof luxon !== 'undefined');
console.log('Luxon adapter loaded successfully via chartjs-adapter-luxon');

const socket = io();

let connected = false;
let logging = false;
let sweeping = false;
let enabledChannels = {};
let loggingStartTime = null;
let lastLogFilename = '';
let detectedChannelCount = 8;

let sessionMax = {
    impedance: 0,
    voltage: 0,
    current: 0,
    power: 0
};

const commandQueue = [];
let isProcessingQueue = false;
let pendingCommandId = 0;
let gainDebounceTimers = {1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null, 8: null};
let generatorFaderDebounceTimers = {1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null, 8: null};

let uploadedVoltageChart = null;
let uploadedCurrentChart = null;
let uploadedPowerChart = null;
let uploadedImpedanceChart = null;

socket.on('connect', () => {
    console.log('Socket.IO connected to server');
});

socket.on('disconnect', () => {
    console.log('Socket.IO disconnected from server');
});


const impedanceHistory = {
    1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []
};
const voltageHistory = {
    1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []
};
const currentHistory = {
    1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []
};
const powerHistory = {
    1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []
};

let impedanceChart = null;
let voltageChart = null;
let currentChart = null;
let powerChart = null;

let gainUpdateTimeout = null;
let chartRefreshInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('=== Page Load Started ===');
    console.log('Chart.js available:', typeof Chart !== 'undefined');
    console.log('Socket.IO available:', typeof io !== 'undefined');
    console.log('Luxon available:', typeof luxon !== 'undefined');

    try {
        console.log('Attempting to initialize charts...');
        initializeCharts();
        console.log('Charts initialized successfully!');
        console.log('Chart objects created:', {
            impedance: !!impedanceChart,
            voltage: !!voltageChart,
            current: !!currentChart,
            power: !!powerChart
        });
    } catch (error) {
        console.error('FATAL ERROR initializing charts:', error);
        console.error('Error stack:', error.stack);
        console.error('Failed to initialize charts. Check console for details.');
        return;
    }

    try {
        attachEventListeners();
        console.log('Event listeners attached successfully');
    } catch (error) {
        console.error('Error attaching event listeners:', error);
    }

    try {
        setupSocketListeners();
        console.log('Socket listeners configured successfully');
    } catch (error) {
        console.error('Error setting up socket listeners:', error);
    }

    try {
        setupPlotsToggle();
        console.log('Plots toggle initialized');
    } catch (error) {
        console.error('Error setting up plots toggle:', error);
    }

    console.log('=== Page Load Complete ===');
});

function getTimeScaleConfig() {
    return {
        type: 'time',
        display: true,
        time: {
            unit: 'second',
            displayFormats: {
                second: 'HH:mm:ss',
                minute: 'HH:mm:ss',
                hour: 'HH:mm:ss'
            },
            tooltipFormat: 'HH:mm:ss'
        },
        ticks: {
            color: '#cccccc',
            autoSkip: true,
            maxRotation: 45,
            minRotation: 0
        },
        grid: {
            display: true,
            color: '#4a4a4a'
        },
        title: {
            display: true,
            text: 'Time',
            color: '#ffffff',
            font: {
                weight: 'bold'
            }
        }
    };
}

function initializeCharts() {
    console.log('=== Initializing Charts ===');

    const canvasIds = ['impedance-chart', 'voltage-chart', 'current-chart', 'power-chart'];
    const missingCanvases = canvasIds.filter(id => !document.getElementById(id));

    if (missingCanvases.length > 0) {
        const errorMsg = `CRITICAL: Missing canvas elements: ${missingCanvases.join(', ')}`;
        console.error(errorMsg);
        throw new Error(errorMsg);
    }

    console.log('All canvas elements found in DOM');

    const impedanceCanvas = document.getElementById('impedance-chart');
    console.log('Impedance canvas element:', impedanceCanvas);
    console.log('Canvas dimensions:', impedanceCanvas?.width, 'x', impedanceCanvas?.height);

    if (!impedanceCanvas) {
        const errorMsg = 'CRITICAL: Cannot find impedance-chart canvas element in DOM';
        console.error(errorMsg);
        throw new Error(errorMsg);
    }

    let impedanceCtx;
    try {
        impedanceCtx = impedanceCanvas.getContext('2d');
        console.log('Impedance canvas context created:', !!impedanceCtx);
    } catch (error) {
        console.error('Failed to get 2d context for impedance chart:', error);
        throw error;
    }

    console.log('Creating impedance chart...');

    try {
        impedanceChart = new Chart(impedanceCtx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Channel 1',
                        data: [],
                        borderColor: '#FF8C00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 2',
                        data: [],
                        borderColor: '#87CEEB',
                        backgroundColor: 'rgba(135, 206, 235, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 3',
                        data: [],
                        borderColor: '#32CD32',
                        backgroundColor: 'rgba(50, 205, 50, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 4',
                        data: [],
                        borderColor: '#9370DB',
                        backgroundColor: 'rgba(147, 112, 219, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 5',
                        data: [],
                        borderColor: '#FFFFFF',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 6',
                        data: [],
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 7',
                        data: [],
                        borderColor: '#FF4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 8',
                        data: [],
                        borderColor: '#8B4513',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Load Impedance (Ω)',
                        color: '#ffffff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            },
                            filter: function(legendItem, data) {
                                return true;
                            }
                        }
                    },
                    tooltip: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        display: true,
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Impedance (Ω)',
                            color: '#ffffff',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            color: '#cccccc'
                        },
                        grid: {
                            display: true,
                            color: '#4a4a4a'
                        }
                    },
                    x: getTimeScaleConfig()
                }
            }
        });
        console.log('Impedance chart created successfully:', !!impedanceChart);
        console.log('Impedance chart instance:', impedanceChart);
    } catch (error) {
        console.error('FAILED to create impedance chart:', error);
        console.error('Error details:', error.message);
        console.error('Error stack:', error.stack);
        throw error;
    }

    console.log('Creating voltage chart...');
    const voltageCanvas = document.getElementById('voltage-chart');
    const voltageCtx = voltageCanvas.getContext('2d');

    try {
        voltageChart = new Chart(voltageCtx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Channel 1',
                        data: [],
                        borderColor: '#FF8C00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 2',
                        data: [],
                        borderColor: '#87CEEB',
                        backgroundColor: 'rgba(135, 206, 235, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 3',
                        data: [],
                        borderColor: '#32CD32',
                        backgroundColor: 'rgba(50, 205, 50, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 4',
                        data: [],
                        borderColor: '#9370DB',
                        backgroundColor: 'rgba(147, 112, 219, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 5',
                        data: [],
                        borderColor: '#FFFFFF',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 6',
                        data: [],
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 7',
                        data: [],
                        borderColor: '#FF4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 8',
                        data: [],
                        borderColor: '#8B4513',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Output Voltage (V)',
                        color: '#ffffff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            },
                            filter: function(legendItem, data) {
                                return true;
                            }
                        }
                    },
                    tooltip: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Voltage (V)',
                            color: '#ffffff',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            color: '#cccccc'
                        },
                        grid: {
                            display: true,
                            color: '#4a4a4a'
                        }
                    },
                    x: getTimeScaleConfig()
                }
            }
        });
        console.log('Voltage chart created successfully:', !!voltageChart);
    } catch (error) {
        console.error('FAILED to create voltage chart:', error);
        throw error;
    }

    console.log('Creating current chart...');
    const currentCanvas = document.getElementById('current-chart');
    const currentCtx = currentCanvas.getContext('2d');

    try {
        currentChart = new Chart(currentCtx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Channel 1',
                        data: [],
                        borderColor: '#FF8C00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 2',
                        data: [],
                        borderColor: '#87CEEB',
                        backgroundColor: 'rgba(135, 206, 235, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 3',
                        data: [],
                        borderColor: '#32CD32',
                        backgroundColor: 'rgba(50, 205, 50, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 4',
                        data: [],
                        borderColor: '#9370DB',
                        backgroundColor: 'rgba(147, 112, 219, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 5',
                        data: [],
                        borderColor: '#FFFFFF',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 6',
                        data: [],
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 7',
                        data: [],
                        borderColor: '#FF4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 8',
                        data: [],
                        borderColor: '#8B4513',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Output Current (A)',
                        color: '#ffffff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            },
                            filter: function(legendItem, data) {
                                return true;
                            }
                        }
                    },
                    tooltip: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Current (A)',
                            color: '#ffffff',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            color: '#cccccc'
                        },
                        grid: {
                            display: true,
                            color: '#4a4a4a'
                        }
                    },
                    x: getTimeScaleConfig()
                }
            }
        });
        console.log('Current chart created successfully:', !!currentChart);
    } catch (error) {
        console.error('FAILED to create current chart:', error);
        throw error;
    }

    console.log('Creating power chart...');
    const powerCanvas = document.getElementById('power-chart');
    const powerCtx = powerCanvas.getContext('2d');

    try {
        powerChart = new Chart(powerCtx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Channel 1',
                        data: [],
                        borderColor: '#FF8C00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 2',
                        data: [],
                        borderColor: '#87CEEB',
                        backgroundColor: 'rgba(135, 206, 235, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 3',
                        data: [],
                        borderColor: '#32CD32',
                        backgroundColor: 'rgba(50, 205, 50, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 4',
                        data: [],
                        borderColor: '#9370DB',
                        backgroundColor: 'rgba(147, 112, 219, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true
                    },
                    {
                        label: 'Channel 5',
                        data: [],
                        borderColor: '#FFFFFF',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 6',
                        data: [],
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 7',
                        data: [],
                        borderColor: '#FF4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    },
                    {
                        label: 'Channel 8',
                        data: [],
                        borderColor: '#8B4513',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.4,
                        borderWidth: 1.5,
                        pointRadius: 1,
                        pointBackgroundColor: '#000000',
                        pointBorderColor: '#000000',
                        pointHoverRadius: 3,
                        spanGaps: true,
                        hidden: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Output Power (W)',
                        color: '#ffffff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12
                            },
                            filter: function(legendItem, data) {
                                return true;
                            }
                        }
                    },
                    tooltip: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Power (W)',
                            color: '#ffffff',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            color: '#cccccc'
                        },
                        grid: {
                            display: true,
                            color: '#4a4a4a'
                        }
                    },
                    x: getTimeScaleConfig()
                }
            }
        });
        console.log('Power chart created successfully:', !!powerChart);
    } catch (error) {
        console.error('FAILED to create power chart:', error);
        throw error;
    }

    syncChartVisibility();
    console.log('=== All 4 charts initialized successfully ===');
}

function queueCommand(command, channel = null) {
    const commandId = pendingCommandId++;
    commandQueue.push({ ...command, id: commandId, channel });
    showCommandStatus('Queued command...', 'pending', channel);
    processCommandQueue();
    return commandId;
}

async function processCommandQueue() {
    if (isProcessingQueue || commandQueue.length === 0) {
        return;
    }

    isProcessingQueue = true;

    while (commandQueue.length > 0) {
        const command = commandQueue.shift();
        showCommandStatus(`Sending ${command.type}...`, 'pending', command.channel);

        try {
            await executeCommand(command);
            showCommandStatus(`${command.type} succeeded`, 'success', command.channel);
            await new Promise(resolve => setTimeout(resolve, 200));
        } catch (error) {
            console.error('Command execution error:', error);
            showCommandStatus(`Failed: ${error.message}`, 'error', command.channel);
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    isProcessingQueue = false;
}

function executeCommand(command) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Command timeout'));
        }, 12000);

        const successHandler = (data) => {
            console.log(`Received response for ${command.type}:`, data);
            clearTimeout(timeout);
            if (data.success !== false) {
                resolve(data);
            } else {
                reject(new Error('Command failed'));
            }
        };

        switch (command.type) {
            case 'set_signal_generator':
                console.log('Registering listener for signal_generator_set');
                socket.once('signal_generator_set', successHandler);
                console.log('Emitting set_signal_generator:', command.payload);
                socket.emit('set_signal_generator', command.payload);
                break;
            case 'enable_channel_generator':
                socket.once('channel_generator_enabled', successHandler);
                socket.emit('enable_channel_generator', command.payload);
                break;
            case 'set_output_gain':
                socket.once('output_gain_set', successHandler);
                socket.emit('set_output_gain', command.payload);
                break;
            default:
                reject(new Error('Unknown command type'));
        }
    });
}

function showCommandStatus(message, type, channel = null) {
    let statusEl;

    if (channel) {
        statusEl = document.getElementById(`ch${channel}-command-status`);
    } else {
        statusEl = document.getElementById('signal-generator-status');
    }

    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = `command-status ${type}`;

    if (type === 'success') {
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'command-status';
        }, 2000);
    }
}

function attachEventListeners() {
    document.getElementById('connect-btn').addEventListener('click', connectToAmp);
    document.getElementById('disconnect-btn').addEventListener('click', disconnectFromAmp);

    document.getElementById('global-signal-type').addEventListener('change', handleSignalTypeChange);
    document.getElementById('global-signal-frequency').addEventListener('input', handleSignalFrequencyChange);

    for (let i = 1; i <= 8; i++) {
        const toggle = document.getElementById(`ch${i}-enable-toggle`);
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                handleChannelToggle(i, e.target.checked);
            });
        }

        const outputGain = document.getElementById(`ch${i}-output-gain`);
        if (outputGain) {
            outputGain.addEventListener('input', (e) => {
                const valueSpan = document.getElementById(`ch${i}-output-gain-value`);
                if (valueSpan) valueSpan.textContent = `${e.target.value} dB`;
                if (enabledChannels[i]) {
                    debouncedGainUpdate(i, parseFloat(e.target.value));
                }
            });
        }

        const generatorFader = document.getElementById(`ch${i}-generator-fader`);
        if (generatorFader) {
            generatorFader.addEventListener('input', (e) => {
                const valueSpan = document.getElementById(`ch${i}-generator-fader-value`);
                if (valueSpan) valueSpan.textContent = `${e.target.value} dB`;
                if (enabledChannels[i]) {
                    debouncedGeneratorFaderUpdate(i, parseFloat(e.target.value));
                }
            });
        }
    }

    updateFrequencyVisibility();

    document.getElementById('start-logging-btn').addEventListener('click', showFilenameInput);
    document.getElementById('filename-go-btn').addEventListener('click', submitFilename);
    document.getElementById('log-filename-input').addEventListener('keypress', handleFilenameKeyPress);
    document.getElementById('stop-logging-btn').addEventListener('click', stopLogging);
    document.getElementById('clear-charts-btn').addEventListener('click', clearCharts);

    document.getElementById('start-sweep-btn').addEventListener('click', startSweep);
    document.getElementById('stop-sweep-btn').addEventListener('click', stopSweep);

    document.getElementById('upload-plot-btn').addEventListener('click', () => {
        document.getElementById('csv-file-input').click();
    });
    document.getElementById('csv-file-input').addEventListener('change', handleCsvUpload);
    document.getElementById('close-uploaded-plot-btn').addEventListener('click', closeUploadedPlot);
}

let signalUpdateTimeout = null;

function throttledGainUpdate() {
    if (gainUpdateTimeout) {
        clearTimeout(gainUpdateTimeout);
    }

    gainUpdateTimeout = setTimeout(() => {
        const channel = parseInt(document.getElementById('test-channel').value);
        const fader = parseFloat(document.getElementById('output-gain').value);

        socket.emit('set_output_gain', {
            channel: channel,
            fader: fader,
            mute: false
        });
    }, 100);
}

function throttledSignalUpdate() {
    if (signalUpdateTimeout) {
        clearTimeout(signalUpdateTimeout);
    }

    signalUpdateTimeout = setTimeout(() => {
        applySignalGenerator();
    }, 300);
}

function setupSocketListeners() {
    socket.on('connection_status', (data) => {
        console.log('Received connection_status:', data);

        connected = data.connected;

        if (!data.connected && data.error) {
            showConnectionError(data.error);
        } else {
            hideConnectionError();
        }

        updateConnectionUI(data.connected, data.address);
    });

    socket.on('impedance', (data) => {
        const channel = parseInt(data.channel);
        const timestamp = Date.now();
        updateImpedanceDisplay(channel, data.impedance);
        latestReceivedValues.impedance[channel] = data.impedance;
        sessionMax.impedance = Math.max(sessionMax.impedance, data.impedance);

        if (logging) {
            if (!lastDataUpdate.impedance[channel]) {
                lastDataUpdate.impedance[channel] = 0;
            }
            if (timestamp - lastDataUpdate.impedance[channel] >= DATA_THROTTLE_MS) {
                if (!impedanceHistory[channel]) {
                    impedanceHistory[channel] = [];
                }
                impedanceHistory[channel].push({ x: timestamp, y: data.impedance });
                updateChart(impedanceChart, impedanceHistory, 'impedance');
                lastDataUpdate.impedance[channel] = timestamp;
            }
        }
    });

    socket.on('voltage', (data) => {
        const channel = parseInt(data.channel);
        const timestamp = Date.now();
        updateVoltageDisplay(channel, data.voltage);
        latestReceivedValues.voltage[channel] = data.voltage;
        sessionMax.voltage = Math.max(sessionMax.voltage, data.voltage);

        if (logging) {
            if (!lastDataUpdate.voltage[channel]) {
                lastDataUpdate.voltage[channel] = 0;
            }
            if (timestamp - lastDataUpdate.voltage[channel] >= DATA_THROTTLE_MS) {
                if (!voltageHistory[channel]) {
                    voltageHistory[channel] = [];
                }
                voltageHistory[channel].push({ x: timestamp, y: data.voltage });
                updateChart(voltageChart, voltageHistory, 'voltage');
                lastDataUpdate.voltage[channel] = timestamp;
            }
        }
    });

    socket.on('current', (data) => {
        const channel = parseInt(data.channel);
        const timestamp = Date.now();
        updateCurrentDisplay(channel, data.current);
        latestReceivedValues.current[channel] = data.current;
        sessionMax.current = Math.max(sessionMax.current, data.current);

        if (logging) {
            if (!lastDataUpdate.current[channel]) {
                lastDataUpdate.current[channel] = 0;
            }
            if (timestamp - lastDataUpdate.current[channel] >= DATA_THROTTLE_MS) {
                if (!currentHistory[channel]) {
                    currentHistory[channel] = [];
                }
                currentHistory[channel].push({ x: timestamp, y: data.current });
                updateChart(currentChart, currentHistory, 'current');
                lastDataUpdate.current[channel] = timestamp;
            }
        }
    });

    socket.on('power', (data) => {
        const channel = parseInt(data.channel);
        const timestamp = Date.now();
        updatePowerDisplay(channel, data.power);
        latestReceivedValues.power[channel] = data.power;
        sessionMax.power = Math.max(sessionMax.power, data.power);

        if (logging) {
            if (!lastDataUpdate.power[channel]) {
                lastDataUpdate.power[channel] = 0;
            }
            if (timestamp - lastDataUpdate.power[channel] >= DATA_THROTTLE_MS) {
                if (!powerHistory[channel]) {
                    powerHistory[channel] = [];
                }
                powerHistory[channel].push({ x: timestamp, y: data.power });
                updateChart(powerChart, powerHistory, 'power');
                lastDataUpdate.power[channel] = timestamp;
            }
        }
    });

    socket.on('logging_status', (data) => {
        logging = data.active;
        updateLoggingUI(data);
    });

    socket.on('sweep_started', (config) => {
        sweeping = true;
        updateSweepUI(true);
        document.getElementById('sweep-progress').style.display = 'block';
    });

    socket.on('sweep_progress', (data) => {
        updateSweepProgress(data);
    });

    socket.on('sweep_complete', () => {
        sweeping = false;
        updateSweepUI(false);
        document.getElementById('sweep-status').textContent = 'Sweep completed successfully';
        setTimeout(() => {
            document.getElementById('sweep-progress').style.display = 'none';
        }, 3000);
    });

    socket.on('sweep_stopped', () => {
        sweeping = false;
        updateSweepUI(false);
        document.getElementById('sweep-status').textContent = 'Sweep stopped by user';
    });

    socket.on('error', (data) => {
        console.error('Server error:', data.message);
    });

    socket.on('channel_count', (data) => {
        console.log(`Detected ${data.count} channels:`, data.channels);
        detectedChannelCount = data.count;
        updateChannelVisibility(data.channels);
    });

    socket.on('power_supply', (data) => {
        updatePowerSupplyDisplay(data);
    });
}

function showConnectionError(message) {
    const errorDiv = document.getElementById('connection-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideConnectionError() {
    const errorDiv = document.getElementById('connection-error');
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
}

function connectToAmp() {
    const address = document.getElementById('amp-address').value;

    hideConnectionError();

    console.log(`Connecting to amp: ${address}`);
    socket.emit('connect_amp', { address });
}

function disconnectFromAmp() {
    hideConnectionError();
    socket.emit('disconnect_amp');
}

function updateConnectionUI(isConnected, address) {
    const statusEl = document.getElementById('connection-status');
    const connectBtn = document.getElementById('connect-btn');
    const disconnectBtn = document.getElementById('disconnect-btn');

    if (isConnected) {
        statusEl.className = 'status-indicator connected';
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;

        for (let i = 1; i <= 8; i++) {
            const toggle = document.getElementById(`ch${i}-enable-toggle`);
            if (toggle) toggle.disabled = false;
        }
        document.getElementById('start-logging-btn').disabled = false;
        document.getElementById('start-sweep-btn').disabled = false;
    } else {
        statusEl.className = 'status-indicator disconnected';
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;

        for (let i = 1; i <= 8; i++) {
            const toggle = document.getElementById(`ch${i}-enable-toggle`);
            if (toggle) {
                toggle.disabled = true;
                toggle.checked = false;
            }
        }
        document.getElementById('start-logging-btn').disabled = true;
        document.getElementById('start-sweep-btn').disabled = true;

        enabledChannels = {};
    }
}

function debouncedGainUpdate(channel, faderValue) {
    if (gainDebounceTimers[channel]) {
        clearTimeout(gainDebounceTimers[channel]);
    }

    gainDebounceTimers[channel] = setTimeout(() => {
        queueCommand({
            type: 'set_output_gain',
            payload: {
                channel: channel,
                fader: faderValue,
                mute: false
            }
        }, channel);
    }, 300);
}

function debouncedGeneratorFaderUpdate(channel, faderValue) {
    if (generatorFaderDebounceTimers[channel]) {
        clearTimeout(generatorFaderDebounceTimers[channel]);
    }

    generatorFaderDebounceTimers[channel] = setTimeout(() => {
        queueCommand({
            type: 'enable_channel_generator',
            payload: {
                channel: channel,
                enabled: true,
                fader: faderValue
            }
        }, channel);
    }, 300);
}

function updateFrequencyVisibility() {
    const signalType = document.getElementById('global-signal-type').value;
    const frequencyControl = document.getElementById('frequency-control');

    if (signalType === 'Tone') {
        frequencyControl.style.display = 'flex';
    } else {
        frequencyControl.style.display = 'none';
    }
}

function handleSignalTypeChange() {
    updateFrequencyVisibility();

    const signalType = document.getElementById('global-signal-type').value;
    const frequency = parseFloat(document.getElementById('global-signal-frequency').value);

    queueCommand({
        type: 'set_signal_generator',
        payload: { type: signalType, frequency: frequency }
    }, null);
}

function handleSignalFrequencyChange() {
    const signalType = document.getElementById('global-signal-type').value;
    const frequency = parseFloat(document.getElementById('global-signal-frequency').value);

    queueCommand({
        type: 'set_signal_generator',
        payload: { type: signalType, frequency: frequency }
    }, null);
}

function handleChannelToggle(channel, enabled) {
    const statusEl = document.getElementById(`ch${channel}-status`);

    if (enabled) {
        statusEl.textContent = 'Enabling...';
        statusEl.classList.remove('enabled');

        const signalType = document.getElementById('global-signal-type').value;
        const frequency = parseFloat(document.getElementById('global-signal-frequency').value);
        const outputGain = parseFloat(document.getElementById(`ch${channel}-output-gain`).value);
        const generatorFader = parseFloat(document.getElementById(`ch${channel}-generator-fader`).value);

        queueCommand({
            type: 'set_signal_generator',
            payload: { type: signalType, frequency: frequency }
        }, channel);

        queueCommand({
            type: 'enable_channel_generator',
            payload: { channel: channel, enabled: true, fader: generatorFader }
        }, channel);

        queueCommand({
            type: 'set_output_gain',
            payload: { channel: channel, fader: outputGain, mute: false }
        }, channel);

        enabledChannels[channel] = true;
        syncChartVisibility();

        setTimeout(() => {
            statusEl.textContent = 'Enabled';
            statusEl.classList.add('enabled');
            showCommandStatus(`Channel ${channel} enabled successfully`, 'success', channel);
        }, 800);

    } else {
        statusEl.textContent = 'Disabling...';
        statusEl.classList.remove('enabled');

        queueCommand({
            type: 'enable_channel_generator',
            payload: { channel: channel, enabled: false, fader: 0 }
        }, channel);

        queueCommand({
            type: 'set_output_gain',
            payload: { channel: channel, fader: -60, mute: true }
        }, channel);

        delete enabledChannels[channel];
        syncChartVisibility();

        setTimeout(() => {
            statusEl.textContent = 'Disabled';
            statusEl.classList.remove('enabled');
            showCommandStatus(`Channel ${channel} disabled successfully`, 'success', channel);
        }, 800);
    }
}

function showFilenameInput() {
    const startBtn = document.getElementById('start-logging-btn');
    const inputContainer = document.getElementById('filename-input-container');
    const filenameInput = document.getElementById('log-filename-input');
    const errorDiv = document.getElementById('filename-error');
    const lastLogDiv = document.getElementById('last-log-reference');

    startBtn.disabled = true;
    inputContainer.style.display = 'flex';
    errorDiv.style.display = 'none';
    filenameInput.classList.remove('error');

    if (lastLogFilename) {
        lastLogDiv.textContent = `Last log: ${lastLogFilename}`;
        lastLogDiv.style.display = 'block';
    }

    setTimeout(() => filenameInput.focus(), 100);
}

function handleFilenameKeyPress(e) {
    if (e.key === 'Enter') {
        submitFilename();
    }
}

function validateFilename(filename) {
    if (!filename || filename.trim() === '') {
        return { valid: false, error: 'Filename cannot be empty' };
    }

    const validPattern = /^[a-zA-Z0-9_\- ]+$/;
    if (!validPattern.test(filename)) {
        return { valid: false, error: 'Filename contains invalid characters. Use only letters, numbers, spaces, dashes, and underscores.' };
    }

    return { valid: true };
}

async function submitFilename() {
    const filenameInput = document.getElementById('log-filename-input');
    const errorDiv = document.getElementById('filename-error');
    const filename = filenameInput.value.trim();

    const validation = validateFilename(filename);
    if (!validation.valid) {
        errorDiv.textContent = validation.error;
        errorDiv.style.display = 'block';
        filenameInput.classList.add('error');
        return;
    }

    const fullFilename = `${filename}.csv`;

    try {
        const response = await fetch('/check_filename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: fullFilename })
        });

        const data = await response.json();

        if (data.exists) {
            errorDiv.textContent = `File "${fullFilename}" already exists. Please choose a different name.`;
            errorDiv.style.display = 'block';
            filenameInput.classList.add('error');
            return;
        }

        startLoggingWithFilename(fullFilename);

    } catch (error) {
        console.error('Error checking filename:', error);
        errorDiv.textContent = 'Error validating filename. Please try again.';
        errorDiv.style.display = 'block';
        filenameInput.classList.add('error');
    }
}

function startLoggingWithFilename(filename) {
    const inputContainer = document.getElementById('filename-input-container');
    const errorDiv = document.getElementById('filename-error');
    const filenameInput = document.getElementById('log-filename-input');

    inputContainer.style.display = 'none';
    errorDiv.style.display = 'none';
    filenameInput.value = '';
    filenameInput.classList.remove('error');

    lastLogFilename = filename;

    socket.emit('start_logging', { filename: filename });
}

function stopLogging() {
    socket.emit('stop_logging');

    const startBtn = document.getElementById('start-logging-btn');
    startBtn.disabled = false;
}

function fillChartsWithLastKnownValues() {
    const now = Date.now();
    const metricConfigs = [
        { history: voltageHistory, chart: voltageChart, update: lastDataUpdate.voltage, latest: latestReceivedValues.voltage, key: 'voltage' },
        { history: currentHistory, chart: currentChart, update: lastDataUpdate.current, latest: latestReceivedValues.current, key: 'current' },
        { history: powerHistory, chart: powerChart, update: lastDataUpdate.power, latest: latestReceivedValues.power, key: 'power' },
        { history: impedanceHistory, chart: impedanceChart, update: lastDataUpdate.impedance, latest: latestReceivedValues.impedance, key: 'impedance' }
    ];

    metricConfigs.forEach(({ history, chart, update, latest, key }) => {
        let chartNeedsUpdate = false;
        for (let ch = 1; ch <= 8; ch++) {
            if (now - (update[ch] || 0) >= 500) {
                if (!history[ch]) {
                    history[ch] = [];
                }
                let fillValue;
                if (history[ch].length > 0) {
                    fillValue = history[ch][history[ch].length - 1].y;
                } else if (latest[ch] !== undefined) {
                    fillValue = latest[ch];
                } else {
                    continue;
                }
                history[ch].push({ x: now, y: fillValue });
                update[ch] = now;
                chartNeedsUpdate = true;
            }
        }
        if (chartNeedsUpdate) {
            updateChart(chart, history, key);
        }
    });
}

function updateLoggingUI(data) {
    const statusEl = document.getElementById('logging-status');
    const pathEl = document.getElementById('log-file-path');
    const startBtn = document.getElementById('start-logging-btn');
    const stopBtn = document.getElementById('stop-logging-btn');

    if (data.active) {
        statusEl.textContent = 'Logging Active';
        statusEl.className = 'status-text';
        pathEl.textContent = `File: ${data.path}`;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        if (!chartRefreshInterval) {
            chartRefreshInterval = setInterval(fillChartsWithLastKnownValues, 500);
        }
    } else {
        statusEl.textContent = 'Not Logging';
        statusEl.className = 'status-text';
        pathEl.textContent = '';
        startBtn.disabled = false;
        stopBtn.disabled = true;
        if (chartRefreshInterval) {
            clearInterval(chartRefreshInterval);
            chartRefreshInterval = null;
        }
    }
}

function startSweep() {
    const config = {
        start_freq: parseFloat(document.getElementById('sweep-start-freq').value),
        end_freq: parseFloat(document.getElementById('sweep-end-freq').value),
        freq_step: parseFloat(document.getElementById('sweep-freq-step').value),
        start_power: parseFloat(document.getElementById('sweep-start-power').value),
        end_power: parseFloat(document.getElementById('sweep-end-power').value),
        power_step: parseFloat(document.getElementById('sweep-power-step').value),
        dwell_time: parseFloat(document.getElementById('sweep-dwell').value),
        channel: parseInt(document.getElementById('test-channel').value),
        signal_type: document.getElementById('sweep-signal-type').value,
        mode: 'automatic'
    };

    socket.emit('start_sweep', config);
}

function stopSweep() {
    socket.emit('stop_sweep');
}

function updateSweepUI(active) {
    const startBtn = document.getElementById('start-sweep-btn');
    const stopBtn = document.getElementById('stop-sweep-btn');

    startBtn.disabled = active;
    stopBtn.disabled = !active;
}

function updateSweepProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const statusText = document.getElementById('sweep-status');

    progressFill.style.width = `${data.progress_percent}%`;
    statusText.textContent =
        `Testing: ${data.frequency} Hz @ ${data.power_db} dB (Step ${data.step}/${data.total_steps})`;
}

function updateImpedanceDisplay(channel, impedance) {
    const el = document.getElementById(`ch${channel}-impedance`);
    if (el) {
        el.textContent = `${impedance.toFixed(2)} Ω`;
    }
}

function updateVoltageDisplay(channel, voltage) {
    const el = document.getElementById(`ch${channel}-voltage`);
    if (el) {
        el.textContent = `${voltage.toFixed(2)} V`;
    }
}

function updateCurrentDisplay(channel, current) {
    const el = document.getElementById(`ch${channel}-current`);
    if (el) {
        el.textContent = `${current.toFixed(3)} A`;
    }
}

function updatePowerDisplay(channel, power) {
    const el = document.getElementById(`ch${channel}-power`);
    if (el) {
        el.textContent = `${power.toFixed(2)} W`;
    }
}

function updatePowerSupplyDisplay(data) {
    const voltageEl = document.getElementById('ps-ac-voltage');
    const currentEl = document.getElementById('ps-ac-current');
    const wattsEl = document.getElementById('ps-ac-watts');
    const sourceEl = document.getElementById('ps-power-source');
    const statusEl = document.getElementById('ps-status');
    const poeEl = document.getElementById('ps-poe-status');

    if (voltageEl) {
        voltageEl.textContent = `${data.ac_line_voltage.toFixed(1)} V`;
    }
    if (currentEl) {
        currentEl.textContent = `${data.ac_line_current.toFixed(2)} A`;
    }
    if (wattsEl) {
        wattsEl.textContent = `${data.ac_line_watts.toFixed(0)} W`;
    }
    if (sourceEl) {
        sourceEl.textContent = data.power_source || '--';
    }
    if (statusEl) {
        if (data.fault) {
            statusEl.textContent = 'FAULT';
            statusEl.className = 'ps-value ps-status fault';
        } else if (data.thermal) {
            statusEl.textContent = 'THERMAL';
            statusEl.className = 'ps-value ps-status warning';
        } else if (data.line_warning) {
            statusEl.textContent = 'LINE WARNING';
            statusEl.className = 'ps-value ps-status warning';
        } else if (data.power_ok) {
            statusEl.textContent = 'OK';
            statusEl.className = 'ps-value ps-status ok';
        } else {
            statusEl.textContent = '--';
            statusEl.className = 'ps-value ps-status';
        }
    }
    if (poeEl) {
        poeEl.textContent = data.poe_status ? 'Active' : 'Inactive';
    }
}

const MAX_DATA_POINTS = 1000;
const MAX_TIME_WINDOW_MS = 60000;
const DATA_THROTTLE_MS = 100;

const lastDataUpdate = {
    impedance: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0 },
    voltage: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0 },
    current: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0 },
    power: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0 }
};

const latestReceivedValues = {
    impedance: {},
    voltage: {},
    current: {},
    power: {}
};

function updateChart(chart, history, metricKey) {
    chart.data.datasets.forEach((dataset, index) => {
        const channel = index + 1;

        if (!history[channel]) {
            history[channel] = [];
        }

        if (history[channel] && history[channel].length > 0) {
            let data = history[channel];

            const now = Date.now();
            data = data.filter(point => {
                return point.x > (now - MAX_TIME_WINDOW_MS);
            });

            if (data.length > MAX_DATA_POINTS) {
                data = data.slice(-MAX_DATA_POINTS);
            }

            history[channel] = data;
            dataset.data = data;
        }
    });

    if (metricKey && sessionMax[metricKey] > 0) {
        const max = sessionMax[metricKey];
        const padding = Math.max(max * 0.1, 0.1);
        chart.options.scales.y.max = max + padding;
    }

    chart.update('none');
}

function clearCharts() {
    for (let i = 1; i <= 8; i++) {
        impedanceHistory[i] = [];
        voltageHistory[i] = [];
        currentHistory[i] = [];
        powerHistory[i] = [];
        lastDataUpdate.impedance[i] = 0;
        lastDataUpdate.voltage[i] = 0;
        lastDataUpdate.current[i] = 0;
        lastDataUpdate.power[i] = 0;
    }
    loggingStartTime = null;
    sessionMax = { impedance: 0, voltage: 0, current: 0, power: 0 };

    [impedanceChart, voltageChart, currentChart, powerChart].forEach(chart => {
        if (chart) {
            chart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            delete chart.options.scales.y.max;
            chart.update('none');
        }
    });
}

function updateChannelVisibility(availableChannels) {
    const charts = [impedanceChart, voltageChart, currentChart, powerChart];

    charts.forEach(chart => {
        if (!chart) return;

        chart.data.datasets.forEach((dataset, index) => {
            const channel = index + 1;
            dataset.hidden = !availableChannels.includes(channel);
        });

        chart.update('none');
    });

    for (let i = 1; i <= 8; i++) {
        const signalGenColumn = document.querySelector(`.signal-generator-panel .two-column-layout .channel-column:nth-child(${i})`);
        const monitoringCard = document.getElementById(`channel-${i}`);
        const isAvailable = availableChannels.includes(i);

        if (signalGenColumn) {
            signalGenColumn.style.display = isAvailable ? '' : 'none';
        }
        if (monitoringCard) {
            monitoringCard.style.display = isAvailable ? '' : 'none';
        }
    }

    console.log(`UI updated for ${availableChannels.length} channels`);
}

function syncChartVisibility() {
    const anyEnabled = Object.keys(enabledChannels).length > 0;
    const charts = [impedanceChart, voltageChart, currentChart, powerChart];
    charts.forEach(chart => {
        if (!chart) return;
        chart.data.datasets.forEach((dataset, index) => {
            const channel = index + 1;
            dataset.hidden = anyEnabled ? !enabledChannels[channel] : false;
        });
        chart.update('none');
    });
}

function setupPlotsToggle() {
    const toggleBtn = document.getElementById('toggle-plots-btn');
    const monitoringPanel = document.querySelector('.monitoring-panel');

    if (!toggleBtn || !monitoringPanel) {
        console.error('Plots toggle elements not found');
        return;
    }

    const savedState = localStorage.getItem('plotsVisible');
    if (savedState === 'false') {
        monitoringPanel.classList.add('plots-hidden');
        toggleBtn.classList.remove('active');
    }

    toggleBtn.addEventListener('click', () => {
        const isHidden = monitoringPanel.classList.toggle('plots-hidden');
        toggleBtn.classList.toggle('active', !isHidden);
        localStorage.setItem('plotsVisible', !isHidden);
        console.log(`Plots visibility: ${!isHidden ? 'visible' : 'hidden'}`);
    });
}

function getUploadedTimeScaleConfig() {
    return {
        type: 'time',
        display: true,
        time: {
            displayFormats: {
                second: 'HH:mm:ss',
                minute: 'HH:mm:ss',
                hour: 'HH:mm'
            },
            tooltipFormat: 'HH:mm:ss'
        },
        ticks: {
            color: '#cccccc',
            autoSkip: true,
            maxRotation: 45,
            minRotation: 0
        },
        grid: {
            display: true,
            color: '#4a4a4a'
        },
        title: {
            display: true,
            text: 'Time',
            color: '#ffffff',
            font: {
                weight: 'bold'
            }
        }
    };
}

const CHANNEL_COLORS = [
    { border: '#FF8C00', bg: 'rgba(255, 140, 0, 0.1)' },
    { border: '#87CEEB', bg: 'rgba(135, 206, 235, 0.1)' },
    { border: '#32CD32', bg: 'rgba(50, 205, 50, 0.1)' },
    { border: '#9370DB', bg: 'rgba(147, 112, 219, 0.1)' },
    { border: '#FFFFFF', bg: 'rgba(255, 255, 255, 0.1)' },
    { border: '#FFD700', bg: 'rgba(255, 215, 0, 0.1)' },
    { border: '#FF4444', bg: 'rgba(255, 68, 68, 0.1)' },
    { border: '#8B4513', bg: 'rgba(139, 69, 19, 0.1)' }
];

function handleCsvUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const csvText = e.target.result;
        const result = parseCsv(csvText);

        if (result.error) {
            showUploadError(result.error);
            event.target.value = '';
            return;
        }

        hideUploadError();
        renderUploadedPlot(result.data, file.name);
        event.target.value = '';
    };
    reader.readAsText(file);
}

function showUploadError(message) {
    let errorDiv = document.getElementById('upload-error');
    if (!errorDiv) {
        const loggingPanel = document.querySelector('.logging-panel');
        errorDiv = document.createElement('div');
        errorDiv.id = 'upload-error';
        errorDiv.className = 'filename-error';
        loggingPanel.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideUploadError() {
    const errorDiv = document.getElementById('upload-error');
    if (errorDiv) errorDiv.style.display = 'none';
}

function parseCsv(csvText) {
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) {
        return { error: 'File is empty or has no data rows.' };
    }

    const headers = lines[0].split(',').map(h => h.trim());

    const hasTimestamp = headers[0] === 'timestamp';
    const hasTimestampMs = headers[0] === 'timestamp_ms';
    if (!hasTimestamp && !hasTimestampMs) {
        return { error: `Not a ResonX log: first column must be "timestamp" -- found "${headers[0]}".` };
    }

    const channelCols = headers.filter(h => /^ch\d+_/.test(h));
    if (channelCols.length === 0) {
        return { error: 'Not a ResonX log: no channel data columns found (expected columns like ch1_voltage, ch1_impedance, etc.).' };
    }

    const metrics = ['voltage', 'current', 'power', 'impedance'];
    const foundMetrics = metrics.filter(m => headers.some(h => new RegExp(`^ch\\d+_${m}$`).test(h)));
    if (foundMetrics.length === 0) {
        const sampleCols = channelCols.slice(0, 6).join(', ');
        return { error: `No plottable metrics (voltage, current, power, impedance) found. Channel columns present: ${sampleCols}.` };
    }

    const channelData = {
        voltage: {},
        current: {},
        power: {},
        impedance: {}
    };

    const channelIndices = {};
    for (let ch = 1; ch <= 8; ch++) {
        channelIndices[ch] = {
            voltage: headers.indexOf(`ch${ch}_voltage`),
            current: headers.indexOf(`ch${ch}_current`),
            power: headers.indexOf(`ch${ch}_power`),
            impedance: headers.indexOf(`ch${ch}_impedance`)
        };
        channelData.voltage[ch] = [];
        channelData.current[ch] = [];
        channelData.power[ch] = [];
        channelData.impedance[ch] = [];
    }

    if (hasTimestampMs) {
        const msValues = [];
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            const ms = parseFloat(cols[0]);
            if (!isNaN(ms)) msValues.push(ms);
        }
        if (msValues.length === 0) {
            return { error: 'No valid timestamp data found in file.' };
        }
        const minMs = msValues[0];
        const maxMs = msValues[msValues.length - 1];
        const baseTime = Date.now() - (maxMs - minMs);

        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            const ms = parseFloat(cols[0]);
            if (isNaN(ms)) continue;
            const timestamp = baseTime + (ms - minMs);

            for (let ch = 1; ch <= 8; ch++) {
                const idx = channelIndices[ch];
                if (idx.voltage >= 0) {
                    const val = parseFloat(cols[idx.voltage]);
                    if (!isNaN(val)) channelData.voltage[ch].push({ x: timestamp, y: val });
                }
                if (idx.current >= 0) {
                    const val = parseFloat(cols[idx.current]);
                    if (!isNaN(val)) channelData.current[ch].push({ x: timestamp, y: val });
                }
                if (idx.power >= 0) {
                    const val = parseFloat(cols[idx.power]);
                    if (!isNaN(val)) channelData.power[ch].push({ x: timestamp, y: val });
                }
                if (idx.impedance >= 0) {
                    const val = parseFloat(cols[idx.impedance]);
                    if (!isNaN(val)) channelData.impedance[ch].push({ x: timestamp, y: val });
                }
            }
        }
    } else {
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            const timestamp = new Date(cols[0].trim()).getTime();
            if (isNaN(timestamp)) continue;

            for (let ch = 1; ch <= 8; ch++) {
                const idx = channelIndices[ch];
                if (idx.voltage >= 0) {
                    const val = parseFloat(cols[idx.voltage]);
                    if (!isNaN(val)) channelData.voltage[ch].push({ x: timestamp, y: val });
                }
                if (idx.current >= 0) {
                    const val = parseFloat(cols[idx.current]);
                    if (!isNaN(val)) channelData.current[ch].push({ x: timestamp, y: val });
                }
                if (idx.power >= 0) {
                    const val = parseFloat(cols[idx.power]);
                    if (!isNaN(val)) channelData.power[ch].push({ x: timestamp, y: val });
                }
                if (idx.impedance >= 0) {
                    const val = parseFloat(cols[idx.impedance]);
                    if (!isNaN(val)) channelData.impedance[ch].push({ x: timestamp, y: val });
                }
            }
        }
    }

    const totalPoints = Object.values(channelData).reduce((sum, metric) => {
        return sum + Object.values(metric).reduce((s, arr) => s + arr.length, 0);
    }, 0);

    if (totalPoints === 0) {
        return { error: `File has ${lines.length - 1} data rows but no plottable numeric values were found in the ${foundMetrics.join(', ')} columns.` };
    }

    return { data: channelData };
}

function createUploadedChart(canvasId, title, yLabel, channelData, beginAtZero) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');

    const datasets = [];
    let maxVal = 0;

    for (let ch = 1; ch <= 8; ch++) {
        const data = channelData[ch] || [];
        const hasData = data.some(p => p.y !== 0 && p.y !== null);

        for (let j = 0; j < data.length; j++) {
            if (data[j].y > maxVal) maxVal = data[j].y;
        }

        datasets.push({
            label: `Channel ${ch}`,
            data: data,
            borderColor: CHANNEL_COLORS[ch - 1].border,
            backgroundColor: CHANNEL_COLORS[ch - 1].bg,
            tension: 0.4,
            borderWidth: 1.5,
            pointRadius: 0,
            pointHoverRadius: 3,
            spanGaps: true,
            hidden: !hasData
        });
    }

    const yConfig = {
        display: true,
        beginAtZero: beginAtZero,
        title: {
            display: true,
            text: yLabel,
            color: '#ffffff',
            font: { weight: 'bold' }
        },
        ticks: { color: '#cccccc' },
        grid: { display: true, color: '#4a4a4a' }
    };

    if (maxVal > 0 && beginAtZero) {
        const padding = Math.max(maxVal * 0.1, 0.1);
        yConfig.max = maxVal + padding;
    }

    return new Chart(ctx, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    labels: {
                        color: '#ffffff',
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            },
            scales: {
                y: yConfig,
                x: getUploadedTimeScaleConfig()
            }
        }
    });
}

function renderUploadedPlot(channelData, filename) {
    destroyUploadedCharts();

    document.getElementById('uploaded-plot-title').textContent = `Uploaded Plot - ${filename}`;
    document.getElementById('uploaded-plot-panel').style.display = '';

    uploadedVoltageChart = createUploadedChart(
        'uploaded-voltage-chart', 'Output Voltage (V)', 'Voltage (V)',
        channelData.voltage, true
    );
    uploadedCurrentChart = createUploadedChart(
        'uploaded-current-chart', 'Output Current (A)', 'Current (A)',
        channelData.current, true
    );
    uploadedPowerChart = createUploadedChart(
        'uploaded-power-chart', 'Output Power (W)', 'Power (W)',
        channelData.power, true
    );
    uploadedImpedanceChart = createUploadedChart(
        'uploaded-impedance-chart', 'Load Impedance (Ohm)', 'Impedance (Ohm)',
        channelData.impedance, false
    );
}

function destroyUploadedCharts() {
    [uploadedVoltageChart, uploadedCurrentChart, uploadedPowerChart, uploadedImpedanceChart].forEach(chart => {
        if (chart) chart.destroy();
    });
    uploadedVoltageChart = null;
    uploadedCurrentChart = null;
    uploadedPowerChart = null;
    uploadedImpedanceChart = null;
}

function closeUploadedPlot() {
    hideUploadError();
    destroyUploadedCharts();
    document.getElementById('uploaded-plot-panel').style.display = 'none';
}
