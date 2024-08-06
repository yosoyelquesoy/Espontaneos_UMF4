from flask import Flask, request, render_template, redirect, url_for, session, send_file, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

SURVEY_STATUS_FILE = 'survey_status.txt'
SURVEY_SCHEDULE_FILE = 'survey_schedule.txt'
CSV_DIR = 'data_csv'

if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)

def get_csv_file():
    today = datetime.now().strftime('%Y-%m-%d')
    csv_file = os.path.join(CSV_DIR, f'encuestas_{today}.csv')
    return csv_file

def read_status():
    if os.path.exists(SURVEY_STATUS_FILE):
        with open(SURVEY_STATUS_FILE, 'r') as f:
            return f.read().strip()
    return 'closed'

def read_schedule():
    if os.path.exists(SURVEY_SCHEDULE_FILE):
        with open(SURVEY_SCHEDULE_FILE, 'r') as f:
            return f.read().strip().split(',')
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    if read_status() == 'closed':
        return jsonify({'success': False, 'message': 'La encuesta está cerrada.'})
    
    start_time, end_time = read_schedule()
    current_time = datetime.now().strftime('%H:%M')
    if start_time and end_time and not (start_time <= current_time <= end_time):
        return jsonify({'success': False, 'message': 'La encuesta está fuera del horario permitido.'})

    data = request.form.to_dict()
    csv_file = get_csv_file()
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['name', 'email', 'ssn', 'agg', 'phone', 'consultorio', 'turno'])
        writer.writerow(data.values())

    return jsonify({'success': True, 'redirect': url_for('thankyou')})

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['password'] == '1234':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    csv_files = os.listdir(CSV_DIR)
    return render_template('admin_dashboard.html', csv_files=csv_files)

@app.route('/download/<filename>')
def download(filename):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    csv_file = os.path.join(CSV_DIR, filename)
    return send_file(csv_file, as_attachment=True)

@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    csv_file = os.path.join(CSV_DIR, filename)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    return redirect(url_for('admin_dashboard'))

@app.route('/update_survey_status', methods=['POST'])
def update_survey_status():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    status = request.json.get('status')
    with open(SURVEY_STATUS_FILE, 'w') as f:
        f.write(status)
    return jsonify({'success': True})

@app.route('/update_survey_schedule', methods=['POST'])
def update_survey_schedule():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    start_time = request.json.get('startTime')
    end_time = request.json.get('endTime')
    with open(SURVEY_SCHEDULE_FILE, 'w') as f:
        f.write(f"{start_time},{end_time}")
    return jsonify({'success': True})

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        # Lógica para cambiar la contraseña
        return redirect(url_for('admin_dashboard'))
    return render_template('change_password.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return "Todos los datos personales recabados serán confidenciales y utilizados solo para el control interno de citas."

@app.route('/survey_status')
def survey_status():
    return jsonify({'is_open': read_status() == 'open'})

if __name__ == '__main__':
    app.run(debug=True)
