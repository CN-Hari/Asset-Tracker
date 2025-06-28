import gc
import sys
import os
import sqlite3
from flask import Flask, request, render_template_string
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

DB_NAME = 'gps_data.db'

LANDING_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Asset Tracker Home</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: linear-gradient(to right, #f0f4f8, #d9e2ec);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      margin: 0;
    }
    .header {
      background-color: white;
      padding: 0;
      border-bottom: 1px solid #e0e0e0;
    }
    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      padding: 10px 30px 0 30px;
    }
    .logo-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-bottom: 10px;
    }
    .tracker-icon {
      height: 2.5em;
      width: auto;
    }
    .company-name {
      font-size: 1.25rem;
      font-weight: bold;
      color: #e60000;
      margin-top: 0.25rem;
    }

    .navbar-nav {
      display: flex;
      align-items: flex-end;
      font-family: 'Arial', sans-serif;
      font-size: 0.95rem;
      font-weight: 500;
      color: #000;
      padding-bottom: 10px;
    }

    .nav-link {
      padding: 0 12px;
      color: #000;
      text-transform: uppercase;
      font-size: 0.9rem;
      position: relative;
    }

    .nav-item:not(:last-child) {
      border-right: 1px dotted #999;
      margin-right: 12px;
      padding-right: 12px;
    }


    .nav-link:hover {
      color: #e60000;
    }

    .card {
      width: 95%;
      max-width: 900px;
      padding: 80px 60px;
      border-radius: 24px;
      box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
      background-color: #ffffff;
      text-align: center;
      margin: 40px auto;
    }

    h1 {
      font-weight: 700;
      margin-bottom: 50px;
      color: #2c3e50;
      font-size: 2.5rem;
    }

    .btn-lg {
      width: 260px;
      font-size: 1.1rem;
      padding: 14px 20px;
    }

    .btn + .btn {
      margin-left: 20px;
    }

    @media (max-width: 576px) {
      .header-content {
        flex-direction: column;
        align-items: center;
        gap: 10px;
      }

      .navbar-nav {
        flex-direction: column;
        align-items: center;
        padding-bottom: 0;
      }

      .nav-item:not(:last-child) {
        border-right: none;
        margin-right: 0;
      }

      .nav-link::after {
        content: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="header-content">
      <div class="logo-section">
        <img src="{{ url_for('static', filename='Mlogo.png') }}" class="tracker-icon" alt="Muthoot Finance">
        <span class="company-name">MITS CIDRIE</span>
      </div>
      <nav class="navbar navbar-expand">
        <ul class="navbar-nav">
          <li class="nav-item">
            <a class="nav-link" href="/">HOME</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="/tracker">ASSET TRACKER</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="/region-search">REGION SEARCH</a>
          </li>
        </ul>
      </nav>
    </div>
  </div>

  <div class="card">
    <h1>GPS Asset Tracker</h1>
    <div class="d-flex flex-wrap justify-content-center">
      <a href="/tracker" class="btn btn-primary btn-lg mb-2">Device Status</a>
      <a href="/region-search" class="btn btn-outline-secondary btn-lg mb-2">Region Search</a>
    </div>
  </div>
</body>
</html>
"""



TRACKER_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GPS Tracker</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
  <style>
    body {
      padding-top: 20px;
      background-color: #f8f9fa;
    }
    .container {
      max-width: 1200px;
      width: 95%;
    }
    .chart-container {
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 15px;
      margin-bottom: 20px;
      background-color: white;
    }
    .badge {
      font-size: 0.85em;
      padding: 0.35em 0.65em;
      font-weight: 500;
    }
    .card {
      margin-bottom: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .card-header {
      font-weight: 600;
      background-color: #f8f9fa;
    }
    .navbar {
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }
    /* Add this for the tracker icon */
    .tracker-icon {
      height: 1em;
      width: auto;
      vertical-align: middle;
      margin-right: 8px;
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <div class="container-fluid">
    <a class="navbar-brand" href="/">HOME</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link" href="/tracker">
     
            Asset Tracker
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/region-search"> Region Search</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
<div class="container">
  <h2 class="my-4">
    <img src="{{ url_for('static', filename='Mlogo.png') }}" class="tracker-icon" alt="Tracker">
    ASSET TRACKER
  </h2>
 
  <div class="card mb-4">
    <div class="card-header">Upload Data</div>
    <div class="card-body">
      <form method="post" enctype="multipart/form-data">
        <div class="mb-3">
          <label class="form-label">Upload CSV File</label>
          <input class="form-control" type="file" name="file" accept=".csv" required>
        </div>
        <div class="mb-3">
          <label class="form-label">Date Format in File:</label>
          <div class="form-check">
            <input class="form-check-input" type="radio" name="date_format" id="format1" value="mmddyyyy" checked>
            <label class="form-check-label" for="format1">MM/DD/YYYY</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" name="date_format" id="format2" value="ddmmyyyy">
            <label class="form-check-label" for="format2">DD/MM/YYYY</label>
          </div>
        </div>
        <button class="btn btn-primary" type="submit">Upload</button>
      </form>
    </div>
  </div>

  {% if upload_success %}
    <div class="alert alert-success">✅ File uploaded and data imported successfully.</div>
  {% endif %}

  <div class="card mb-4">
    <div class="card-header">Device Search</div>
    <div class="card-body">
      <form method="post">
        <div class="mb-3">
          <label class="form-label">Device ID</label>
          <input type="text" class="form-control" name="device" required value="{{ device_prefill or '' }}">
        </div>
        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label">From Date</label>
            <input type="text" class="form-control datepicker" name="from_date" placeholder="dd/mm/yyyy" required>
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label">To Date</label>
            <input type="text" class="form-control datepicker" name="to_date" placeholder="dd/mm/yyyy" required>
          </div>
        </div>
        <button class="btn btn-success" type="submit">Search</button>
      </form>
    </div>
  </div>

  {% if result %}
    <div class="card mb-4">
      <div class="card-header">Results</div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-6">
            <p><strong>Device:</strong> {{ result['device'] }}</p>
            {% if result['region'] %}
              <p><strong>Region:</strong> {{ result['region'] }}</p>
              <p><strong>Branch:</strong> {{ result['branch'] }}</p>
            {% endif %}
          </div>
          <div class="col-md-6">
            <p><strong>From Date:</strong> {{ result['from_date'] }}</p>
            <p><strong>To Date:</strong> {{ result['to_date'] }}</p>
            <p><strong>Total Pings:</strong> {{ result['pings'] }}</p>
            <p><strong>Total Charges:</strong> {{ result['charges'] }}
              {% if result['long_offline_count'] > 0 %}
                <span class="badge bg-warning text-dark ms-2">
                  {{ result['long_offline_count'] }} long offline period(s)
                </span>
              {% endif %}
            </p>
          </div>
        </div>
       
        {% if result['charge_details'] %}
        <div class="mt-4">
          <h5>Charge Cycle Details</h5>
          <div class="table-responsive">
            <table class="table table-striped">
              <thead>
                <tr>
                  <th>Charge Count</th>
                  <th>Date</th>
                  <th>Start Voltage</th>
                  <th>Max Voltage</th>
                  <th>Start Time</th>
                  <th>End Time</th>
                  <th>Duration</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {% for charge in result['charge_details'] %}
                <tr>
                  <td>{{ loop.index }}</td>
                  <td>{{ charge['date'] }}</td>
                  <td>{{ "%.2f"|format(charge['start_voltage']) }}V</td>
                  <td>{{ "%.2f"|format(charge['max_voltage']) }}V</td>
                  <td>{{ charge['start_time'] }}</td>
                  <td>{{ charge['end_time'] }}</td>
                  <td>{{ charge['duration'] }}</td>
                  <td>
                    {% if charge['is_long_offline'] %}
                      <span class="badge bg-danger">Offline for {{ charge['days_offline'] }}</span>
                    {% else %}
                      <span class="badge bg-success">Normal</span>
                    {% endif %}
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
        {% endif %}
      </div>
    </div>
  {% endif %}

  {% if combined_chart %}
    <div class="card">
      <div class="card-header">Activity Summary</div>
      <div class="card-body">
        <div class="chart-container">
          {{ combined_chart | safe }}
        </div>
      </div>
    </div>
  {% endif %}
</div>

<script>
  flatpickr(".datepicker", {
    dateFormat: "d/m/Y",
    allowInput: true
  });
</script>
</body>
</html>"""

REGION_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Region Search</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      padding-top: 20px;
      background-color: #f8f9fa;
    }
    .container {
      max-width: 1400px;
      width: 95%;
    }
    .card {
      margin-bottom: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .card-header {
      font-weight: 600;
      background-color: #f8f9fa;
      padding: 0.75rem 1rem;
    }
    .navbar {
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }
    .list-group-item {
      transition: all 0.2s;
      padding: 0.75rem 1.25rem;
    }
    .list-group-item:hover {
      background-color: #f8f9fa;
    }
    .badge {
      font-size: 0.85em;
      padding: 0.35em 0.65em;
      font-weight: 500;
    }
    .summary-card {
      height: 100%;
    }
    .summary-card .card-body {
      padding: 1rem;
    }
    .compact-item {
      padding: 0.5rem 1rem;
      border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    .compact-item:last-child {
      border-bottom: none;
    }
    .stat-value {
      font-weight: 600;
      color: #2c3e50;
    }
    /* Add this for the tracker icon */
    .tracker-icon {
      height: 1em;
      width: auto;
      vertical-align: middle;
      margin-right: 8px;
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <div class="container-fluid">
    <a class="navbar-brand" href="/"> HOME</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link" href="/tracker"> Asset Tracker</a>
        </li>
        <li class="nav-item">
          <a class="nav-link active" href="/region-search"> Region Search</a>
        </li>
      </ul>
    </div>
  </div>
</nav>

<div class="container">
  <h2 class="my-4"> <img src="{{ url_for('static', filename='Mlogo.png') }}" class="tracker-icon" alt="Tracker">Region Search</h2>
 
  <div class="row">
    <!-- Left Column - Compact Summary -->
    <div class="col-lg-3 col-md-4">
      <div class="card summary-card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>📊 Device Distribution</span>
        </div>
        <div class="card-body">
          <div class="d-flex justify-content-between compact-item">
            <span>Total Devices:</span>
            <span class="stat-value">{{ total_devices }}</span>
          </div>
          <div class="d-flex justify-content-between compact-item">
            <span>Regions:</span>
            <span class="stat-value">{{ region_count }}</span>
          </div>
         
          <hr class="my-2">
         
          <div class="fw-bold mb-2">Devices by Region:</div>
          <div>
            {% for region in regions_with_counts %}
            <div class="d-flex justify-content-between align-items-center compact-item">
              <span class="text-truncate" title="{{ region.region or 'Unknown' }}">
                {{ region.region or 'Unknown' }}
              </span>
              <span class="badge bg-secondary">{{ region.count }}</span>
            </div>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>

    <!-- Right Column - Main Content -->
    <div class="col-lg-9 col-md-8">
      <!-- Upload Data Card -->
      <div class="card">
        <div class="card-header">Upload Data</div>
        <div class="card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="mb-3">
              <label class="form-label">Upload Region Data File</label>
              <input class="form-control" type="file" name="file" accept=".csv" required>
            </div>
            <button class="btn btn-primary" type="submit">Upload</button>
          </form>
        </div>
      </div>

      {% if upload_success %}
        <div class="alert alert-success">✅ File uploaded and device info imported successfully.</div>
      {% endif %}

      <!-- Device Filter Card -->
      <div class="card">
        <div class="card-header">Device Filter</div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Select Region</label>
            <select class="form-select" id="region-select" onchange="updateBranches()">
              <option value="">-- Select Region --</option>
            </select>
          </div>
         
          <div class="mb-3">
            <div id="branch-count" class="fw-bold text-primary mb-2"></div>
            <label class="form-label">Select Branch</label>
            <select class="form-select" id="branch-select" onchange="updateDevices()">
              <option value="">-- Select Branch --</option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label">Devices in Selected Branch</label>
            <ul class="list-group" id="device-list"></ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  const data = {{ data|tojson }};
  const regionSelect = document.getElementById('region-select');
  const branchSelect = document.getElementById('branch-select');
  const deviceList = document.getElementById('device-list');

  // Initialize regions
  const regions = [...new Set(data.map(item => item.region))].filter(r => r);
  regions.forEach(region => {
    const option = document.createElement('option');
    option.value = region;
    option.text = region;
    regionSelect.appendChild(option);
  });

  function updateBranches() {
    branchSelect.innerHTML = '<option value="">-- Select Branch --</option>';
    deviceList.innerHTML = '';
    document.getElementById('branch-count').textContent = '';

    const selectedRegion = regionSelect.value;
    if (!selectedRegion) return;

    const branches = [...new Set(data
      .filter(item => item.region === selectedRegion && item.branch)
      .map(item => item.branch))];

    branches.forEach(branch => {
      const option = document.createElement('option');
      option.value = branch;
      option.text = branch;
      branchSelect.appendChild(option);
    });

    document.getElementById('branch-count').textContent =
      `${branches.length} ${branches.length === 1 ? 'branch' : 'branches'} found`;
  }

  function updateDevices() {
    deviceList.innerHTML = '';
    const selectedRegion = regionSelect.value;
    const selectedBranch = branchSelect.value;
   
    if (!selectedRegion || !selectedBranch) return;

    const filtered = data.filter(item =>
      item.region === selectedRegion &&
      item.branch === selectedBranch &&
      item.device
    );

    if (filtered.length === 0) {
      const li = document.createElement('li');
      li.className = 'list-group-item text-muted';
      li.textContent = 'No devices found.';
      deviceList.appendChild(li);
    } else {
      filtered.forEach(item => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
          <a href="/tracker?device=${encodeURIComponent(item.device)}" class="text-decoration-none">${item.device}</a>
          <span class="badge bg-secondary">${item.sim_type || 'N/A'}</span>
        `;
        deviceList.appendChild(li);
      });
    }
  }
</script>
</body>
</html>"""

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS gps_data')
        c.execute('''
            CREATE TABLE gps_data (
                sl_no INTEGER,
                device TEXT,
                event TEXT,
                tracking_date TEXT,
                battery_voltage REAL,
                FOREIGN KEY (device) REFERENCES device_info(device)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_device ON gps_data(device)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_date ON gps_data(tracking_date)')

def init_device_info_table():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS device_info (
                device TEXT PRIMARY KEY,
                region TEXT,
                branch TEXT,
                sim_type TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_region ON device_info(region)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_branch ON device_info(branch)')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def import_device_info(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    required = ['device_id', 'region', 'branch', 'sim_type']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in metadata: {missing}")

    df = df[required]
    df.rename(columns={'device_id': 'device'}, inplace=True)
    df.dropna(subset=['device'], inplace=True)

    with sqlite3.connect(DB_NAME) as conn:
        df.to_sql('device_info', conn, if_exists='replace', index=False)

def import_csv(file_path, date_format='mmddyyyy'):
    df = pd.read_csv(file_path, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    column_mapping = {'sl._no': 'sl_no', 'event_type': 'event'}
    df.rename(columns=column_mapping, inplace=True)

    required = ['sl_no', 'device', 'event', 'tracking_date', 'battery_voltage']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[required]

    # Normalize text
    df['event'] = df['event'].astype(str).str.strip().str.upper()
    df['device'] = df['device'].astype(str).str.strip()

    # Clean and convert tracking_date based on selected format
    df['tracking_date'] = df['tracking_date'].astype(str).str.strip()
   
    # First try parsing with the specified format
    try:
        if date_format == 'ddmmyyyy':
            df['tracking_date'] = pd.to_datetime(df['tracking_date'], dayfirst=True, errors='raise')
        else:  # default to mm/dd/yyyy
            df['tracking_date'] = pd.to_datetime(df['tracking_date'], format='%m/%d/%Y %I:%M:%S %p', errors='raise')
    except:
        # If format parsing fails, try more flexible parsing
        try:
            df['tracking_date'] = pd.to_datetime(df['tracking_date'], errors='coerce')
        except:
            raise ValueError("Could not parse dates with either specified format or flexible parsing")

    # Ensure battery voltage is numeric
    df['battery_voltage'] = pd.to_numeric(df['battery_voltage'], errors='coerce')
    df.dropna(subset=['tracking_date', 'battery_voltage', 'device'], inplace=True)

    with sqlite3.connect(DB_NAME) as conn:
        df.to_sql('gps_data', conn, if_exists='append', index=False)
       
def detect_charges(df, rise_threshold=0.15, window=3):
    df = df.sort_values('tracking_date').reset_index(drop=True)
    voltages = df['battery_voltage'].tolist()
    timestamps = df['tracking_date'].tolist()
    raw_charges = []
    i = 0

    while i < len(voltages) - window:
        start_voltage = voltages[i]
        end_voltage = voltages[i + window]

        if pd.notna(start_voltage) and pd.notna(end_voltage) and end_voltage - start_voltage >= rise_threshold:
            max_voltage = max(voltages[i:i+window+1])
            max_index = i + voltages[i:i+window+1].index(max_voltage)

            start_time = timestamps[i]
            end_time = timestamps[max_index]
            charge_duration = end_time - start_time
            days_offline = charge_duration.total_seconds() / (24 * 3600)

            raw_charges.append({
                'start_time_dt': start_time,
                'end_time_dt': end_time,
                'date': start_time.date(),
                'start_voltage': start_voltage,
                'max_voltage': max_voltage,
                'duration': charge_duration,
                'days_offline': days_offline,
                'is_long_offline': days_offline >= 2
            })

            i = max_index
        else:
            i += 1

    # Merge nearby events (<30 mins apart)
    merged_charges = []
    for charge in raw_charges:
        if not merged_charges:
            merged_charges.append(charge)
            continue

        last = merged_charges[-1]
        if charge['start_time_dt'] - last['end_time_dt'] <= timedelta(minutes=60):
            # Merge into last
            last['end_time_dt'] = max(last['end_time_dt'], charge['end_time_dt'])
            last['max_voltage'] = max(last['max_voltage'], charge['max_voltage'])
            last['start_voltage'] = min(last['start_voltage'], charge['start_voltage'])
            last['duration'] = last['end_time_dt'] - last['start_time_dt']
            last['days_offline'] = last['duration'].total_seconds() / (24 * 3600)
            last['is_long_offline'] = last['days_offline'] >= 2
        else:
            merged_charges.append(charge)

    # Format result for template
    for charge in merged_charges:
        charge['start_time'] = charge['start_time_dt'].strftime('%I:%M:%S %p')
        charge['end_time'] = charge['end_time_dt'].strftime('%I:%M:%S %p')
        charge['date'] = charge['start_time_dt'].strftime('%d-%m-%Y')

        total_seconds = charge['duration'].total_seconds()
        days = int(total_seconds // 86400)
        hours = int((total_seconds % 86400) // 3600)
        minutes = int((total_seconds % 3600) // 60)
        charge['duration'] = f"{days} days {hours} hrs {minutes} mins"
       
        if charge['is_long_offline']:
            charge['days_offline'] = f"{days} days {hours} hrs {minutes} mins"

    return merged_charges

def create_combined_chart(ping_series, charge_details, full_voltage_df, title="Activity Summary"):
    try:
        fig = go.Figure()

        # ===== 1. Convert and validate ping_series =====
        if not isinstance(ping_series, (pd.Series, list)):
            ping_series = pd.Series(ping_series)
       
        ping_series = pd.to_datetime(ping_series, errors='coerce').dropna()
       
        if ping_series.empty:
            app.logger.warning("No valid ping dates found")
            return None

        # ===== 2. Prepare charge details =====
        charge_dates = []
        highlight_x = []
        highlight_y = []
        highlight_text = []

        for charge in charge_details:
            try:
                start_dt = pd.to_datetime(charge['start_time_dt'])
                end_dt = pd.to_datetime(charge['end_time_dt'])
               
                charge_dates.append(start_dt)
               
                # Min voltage point
                highlight_x.append(start_dt)
                highlight_y.append(charge['start_voltage'])
                highlight_text.append(
                    f"Start Voltage: {charge['start_voltage']:.2f}V<br>"
                    f"Date: {start_dt.strftime('%d-%m-%Y %I:%M %p')}"
                )

                # Max voltage point
                highlight_x.append(end_dt)
                highlight_y.append(charge['max_voltage'])
                highlight_text.append(
                    f"Max Voltage: {charge['max_voltage']:.2f}V<br>"
                    f"Date: {end_dt.strftime('%d-%m-%Y %I:%M %p')}"
                )
            except (KeyError, ValueError) as e:
                app.logger.warning(f"Skipping invalid charge entry: {e}")
                continue

        # ===== 3. Create ping count bars =====
        ping_counts = ping_series.value_counts().sort_index()
        ping_dates = sorted(ping_counts.index)
       
        fig.add_trace(go.Bar(
            x=ping_dates,
            y=[ping_counts.get(date, 0) for date in ping_dates],
            name="Ping Count",
            marker_color='rgba(54, 162, 235, 0.7)',
            yaxis='y1',
            hovertemplate='Date: %{x}<br>Pings: %{y}<extra></extra>'
        ))

        # ===== 4. Add battery voltage line =====
        if not full_voltage_df.empty:
            fig.add_trace(go.Scatter(
                x=full_voltage_df['tracking_date'],
                y=full_voltage_df['battery_voltage'],
                mode='lines',
                name='Battery Voltage',
                line=dict(color='orange', width=2),
                yaxis='y2',
                hovertemplate='Date: %{x|%d-%m-%Y %I:%M %p}<br>Voltage: %{y:.2f}V<extra></extra>'
            ))

        # ===== 5. Add charge markers =====
        if highlight_x:
            fig.add_trace(go.Scatter(
                x=highlight_x,
                y=highlight_y,
                mode='markers',
                name='Charge Min/Max Points',
                marker=dict(color='orange', size=8, symbol='circle'),
                yaxis='y2',
                text=highlight_text,
                hoverinfo='text'
            ))

        # ===== 6. Handle date ranges and monthly grouping =====
        min_date = ping_series.min()
        max_date = ping_series.max()
        date_range = (max_date - min_date).days

        # Determine if we should show monthly or daily ticks
        if date_range > 60:  # More than 2 months - use monthly grouping
            monthly_pings = ping_series.groupby([
                ping_series.dt.year.rename('year'),
                ping_series.dt.month.rename('month')
            ]).size()
           
            if charge_dates:
                charge_series = pd.Series(charge_dates)
                monthly_charges = charge_series.groupby([
                    charge_series.dt.year.rename('year'),
                    charge_series.dt.month.rename('month')
                ]).size()
            else:
                monthly_charges = pd.Series(dtype=int)
           
            # Create month labels
            all_months = set()
            for dt in ping_dates:
                all_months.add((dt.year, dt.month))
            if charge_dates:
                for dt in charge_dates:
                    all_months.add((dt.year, dt.month))
           
            sorted_months = sorted(all_months)
            month_centers = []
            month_labels = []
           
            for year, month in sorted_months:
                middle = datetime(year, month, 15, 12, 0, 0)
                month_centers.append(middle)
                ping_count = monthly_pings.get((year, month), 0)
                charge_count = monthly_charges.get((year, month), 0)
                month_labels.append(f"{middle.strftime('%b %Y')}<br>Pings: {ping_count} | Charges: {charge_count}")
               
                # Add vertical lines for month starts
                if datetime(year, month, 1) > min_date:
                    fig.add_vline(
                        x=datetime(year, month, 1),
                        line_dash="dot",
                        line_color="gray",
                        line_width=1,
                        opacity=0.5
                    )
           
            xaxis_config = {
                'title': "Month",
                'tickvals': month_centers,
                'ticktext': month_labels,
                'tickangle': 0,
                'tickfont': dict(size=10)
            }
        else:
            # For short ranges (<2 months), use daily ticks
            xaxis_config = {
                'title': "Date",
                'tickformat': "%d %b",
                'tickangle': 45
            }

        # ===== 7. Final layout =====
        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis=xaxis_config,
            yaxis=dict(title="Ping Count", side='left', showgrid=False),
            yaxis2=dict(
                title="Battery Voltage (V)",
                overlaying='y',
                side='right',
                showgrid=False,
                range=[2.8, 4.4]
            ),
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
            margin=dict(l=40, r=40, t=50, b=120),
            height=450,
            dragmode=False
        )

        return pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs='cdn',
            config={
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'scrollZoom': False,
                'displayModeBar': True,
                'displaylogo': False
            }
        )

    except Exception as e:
        app.logger.error(f"Error in create_combined_chart: {str(e)}")
        return None
@app.route('/')
def landing():
    return render_template_string(LANDING_TEMPLATE)

@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    result = None
    combined_chart = None
    upload_success = False
    device_prefill = request.args.get('device', '')

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(f"{uuid.uuid4()}.csv")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Get selected date format (default to mm/dd/yyyy if not specified)
                date_format = request.form.get('date_format', 'mmddyyyy')

                # Check file type by looking at columns
                df_preview = pd.read_csv(file_path, nrows=5)
                cols = df_preview.columns.str.lower().str.replace(' ', '_')
                if set(['device_id', 'region', 'branch']).issubset(cols):
                    init_device_info_table()
                    import_device_info(file_path)
                else:
                    init_db()
                    import_csv(file_path, date_format=date_format)
               
                upload_success = True
                os.remove(file_path)
            except Exception as e:
                return render_template_string(TRACKER_TEMPLATE,
                                           error_message=f"Error processing file: {str(e)}")

    elif all(k in request.form for k in ('device', 'from_date', 'to_date')):
        device = request.form['device'].strip()
        from_date_raw = request.form['from_date']
        to_date_raw = request.form['to_date']
       
        try:
            from_date = pd.to_datetime(from_date_raw, dayfirst=True).strftime('%Y-%m-%d')
            to_date = pd.to_datetime(to_date_raw, dayfirst=True).strftime('%Y-%m-%d')
        except Exception as e:
            return render_template_string(TRACKER_TEMPLATE,
                                       error_message=f"Invalid date format: {str(e)}")

        with sqlite3.connect(DB_NAME) as conn:
            # Get GPS data
            df = pd.read_sql_query('''
                SELECT * FROM gps_data
                WHERE device = ?
                  AND DATE(tracking_date) BETWEEN DATE(?) AND DATE(?)
                ORDER BY tracking_date
            ''', conn, params=(device, from_date, to_date))

            # Get device info
            cur = conn.cursor()
            cur.execute('SELECT region, branch FROM device_info WHERE device = ?', (device,))
            info = cur.fetchone()

        if not df.empty:
            df['event'] = df['event'].astype(str).str.strip().str.upper()
            df['tracking_date'] = pd.to_datetime(df['tracking_date'], errors='coerce')

            # Process pings
            pings = df[df['event'].isin(['G_PING', 'REBOOT'])]
            ping_dates = pings['tracking_date'].dt.date

            # Process charges - now returns detailed charge information
            charge_details = detect_charges(df)

            result = {
                'device': device,
                'from_date': from_date_raw,
                'to_date': to_date_raw,
                'pings': len(ping_dates),
                'charges': len(charge_details),
                'charge_details': charge_details,
                'long_offline_count': sum(1 for c in charge_details if c['is_long_offline'])
            }

            if info:
                result['region'] = info[0]
                result['branch'] = info[1]

            if not ping_dates.empty or charge_details:
                # Extract just the dates for the chart
                charge_dates = pd.Series([c['start_time_dt'].date() for c in charge_details])
                full_voltage_df = df[['tracking_date', 'battery_voltage']].dropna()
                combined_chart = create_combined_chart(ping_dates, charge_details, full_voltage_df)

    return render_template_string(
        TRACKER_TEMPLATE,
        result=result,
        combined_chart=combined_chart,
        upload_success=upload_success,
        device_prefill=device_prefill
    )

@app.route('/region-search', methods=['GET', 'POST'])
def region_search():
    upload_success = False

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(f"{uuid.uuid4()}.csv")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
               
                init_device_info_table()
                import_device_info(file_path)
                upload_success = True
                os.remove(file_path)
            except Exception as e:
                return render_template_string(REGION_TEMPLATE,
                                           error_message=f"Error uploading file: {str(e)}")

    # Load device_info and calculate counts
    with sqlite3.connect(DB_NAME) as conn:
        # Ensure table exists before querying
        conn.execute('''
            CREATE TABLE IF NOT EXISTS device_info (
                device TEXT PRIMARY KEY,
                region TEXT,
                branch TEXT,
                sim_type TEXT
            )
        ''')
   
        try:
            df = pd.read_sql_query('SELECT * FROM device_info', conn)
        except pd.io.sql.DatabaseError:
            df = pd.DataFrame(columns=['device', 'region', 'branch', 'sim_type'])

        # Calculate counts
        total_devices = len(df)
        region_count = df['region'].nunique()
       
        # Get device count per region
        regions_with_counts = df.groupby('region').size().reset_index(name='count')
        regions_with_counts = regions_with_counts.to_dict('records')

    return render_template_string(
        REGION_TEMPLATE,
        upload_success=upload_success,
        data=df.to_dict(orient='records'),
        total_devices=total_devices,
        region_count=region_count,
        regions_with_counts=regions_with_counts
    )
if __name__ == '__main__':
    app.run(debug=True)



	

