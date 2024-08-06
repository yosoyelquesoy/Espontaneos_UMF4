from flask import Flask, request, render_template, redirect, url_for, session, send_file, jsonify, flash
import csv
import os
import json
from datetime import datetime
import pytz
import logging

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de logging para errores
logging.basicConfig(filename='error.log', level=logging.ERROR)

CONFIG_FILE = 'config.json'
ADMIN_FILE = 'admin.json'
CSV_DIR = 'data_csv'
TIMEZONE = 'Etc/GMT+7'  # GMT-7

if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'status': 'closed',
        'start_time': None,
        'end_time': None
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_admin():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, 'r') as f:
            return json.load(f)
    return {
        'email': 'admin@example.com',
        'password': '1234'
    }

def save_admin(admin):
    with open(ADMIN_FILE, 'w') as f:
        json.dump(admin, f)

def get_csv_file():
    today = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
    csv_file = os.path.join(CSV_DIR, f'encuestas_{today}.csv')
    return csv_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        config = load_config()
        if config['status'] == 'closed':
            return jsonify({'success': False, 'message': 'La encuesta está cerrada.'})

        current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M')
        start_time = config['start_time']
        end_time = config['end_time']
        if start_time and end_time and not (start_time <= current_time <= end_time):
            return jsonify({'success': False, 'message': 'La encuesta está fuera del horario permitido.'})

        data = {key: value.upper() for key, value in request.form.items()}
        data['Fecha'] = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
        data['Hora'] = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
        csv_file = get_csv_file()
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Fecha', 'Hora', 'Nombre', 'Email', 'NSS', 'Agregado', 'Teléfono', 'Consultorio', 'Turno'])
            writer.writerow([data['Fecha'], data['Hora'], data['Nombre'], data['email'], data['NSS'], data['Agregado'], data['Telefono'], data['Consultorio'], data['Turno']])

        return jsonify({'success': True, 'redirect': url_for('thankyou')})
    except Exception as e:
        logging.error(f"Error in /submit: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor.'})

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    try:
        error = None
        if request.method == 'POST':
            admin_data = load_admin()
            if request.form['password'] == admin_data['password']:
                session['admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                error = 'Contraseña incorrecta'
        return render_template('admin.html', error=error)
    except Exception as e:
        logging.error(f"Error in /admin: {e}")
        return render_template('admin.html', error="Error interno del servidor.")

@app.route('/admin_dashboard')
def admin_dashboard():
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        config = load_config()
        csv_files = os.listdir(CSV_DIR)
        success_message = request.args.get('success')
        return render_template('admin_dashboard.html', config=config, csv_files=csv_files, success=success_message)
    except Exception as e:
        logging.error(f"Error in /admin_dashboard: {e}")
        return redirect(url_for('admin'))

@app.route('/download/<filename>')
def download(filename):
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        csv_file = os.path.join(CSV_DIR, filename)
        return send_file(csv_file, as_attachment=True)
    except Exception as e:
        logging.error(f"Error in /download: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        csv_file = os.path.join(CSV_DIR, filename)
        if os.path.exists(csv_file):
            os.remove(csv_file)
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        logging.error(f"Error in /delete: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/update_survey_status', methods=['POST'])
def update_survey_status():
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        status = request.form.get('status')
        config = load_config()
        config['status'] = status
        save_config(config)
        return redirect(url_for('admin_dashboard', success='Estado de la encuesta actualizado con éxito.'))
    except Exception as e:
        logging.error(f"Error in /update_survey_status: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/update_survey_schedule', methods=['POST'])
def update_survey_schedule():
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        config = load_config()
        config['start_time'] = start_time
        config['end_time'] = end_time
        save_config(config)
        return redirect(url_for('admin_dashboard', success='Horario de la encuesta actualizado con éxito.'))
    except Exception as e:
        logging.error(f"Error in /update_survey_schedule: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    try:
        if not session.get('admin'):
            return redirect(url_for('admin'))
        if request.method == 'POST':
            admin_data = load_admin()
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if old_password != admin_data['password']:
                flash('Contraseña anterior incorrecta')
            elif new_password != confirm_password:
                flash('La nueva contraseña y la confirmación no coinciden')
            else:
                admin_data['password'] = new_password
                save_admin(admin_data)
                return redirect(url_for('admin_dashboard', success='Contraseña actualizada con éxito.'))
        return render_template('change_password.html')
    except Exception as e:
        logging.error(f"Error in /change_password: {e}")
        return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    try:
        session.pop('admin', None)
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in /logout: {e}")
        return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return "Todos los datos personales recabados serán confidenciales y utilizados solo para el control interno de citas."

@app.route('/survey_status')
def survey_status():
    try:
        config = load_config()
        return jsonify({'is_open': config['status'] == 'open'})
    except Exception as e:
        logging.error(f"Error in /survey_status: {e}")
        return jsonify({'is_open': False})

if __name__ == '__main__':
    app.run(debug=True)
