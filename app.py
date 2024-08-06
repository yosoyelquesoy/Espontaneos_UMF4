from flask import Flask, request, render_template, redirect, url_for, session, send_file, jsonify, flash
from flask_mail import Mail, Message
import csv
import os
import json
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Reemplaza con tu servidor SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu-email@example.com'  # Reemplaza con tu correo
app.config['MAIL_PASSWORD'] = 'tu-contraseña'  # Reemplaza con tu contraseña
app.config['MAIL_DEFAULT_SENDER'] = 'tu-email@example.com'  # Reemplaza con tu correo

mail = Mail(app)

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

def send_reset_email(email, reset_link):
    try:
        msg = Message('Restablecimiento de contraseña', recipients=[email])
        msg.body = f"Para restablecer su contraseña, haga clic en el siguiente enlace: {reset_link}"
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

def get_csv_file():
    today = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
    csv_file = os.path.join(CSV_DIR, f'encuestas_{today}.csv')
    return csv_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
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

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        admin_data = load_admin()
        if request.form['password'] == admin_data['password']:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Contraseña incorrecta')
    return render_template('admin.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    config = load_config()
    admin_data = load_admin()
    csv_files = os.listdir(CSV_DIR)
    success_message = request.args.get('success')
    return render_template('admin_dashboard.html', config=config, csv_files=csv_files, success=success_message, admin_email=admin_data['email'])

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
    status = request.form.get('status')
    config = load_config()
    config['status'] = status
    save_config(config)
    return redirect(url_for('admin_dashboard', success='Estado de la encuesta actualizado con éxito.'))

@app.route('/update_survey_schedule', methods=['POST'])
def update_survey_schedule():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    config = load_config()
    config['start_time'] = start_time
    config['end_time'] = end_time
    save_config(config)
    return redirect(url_for('admin_dashboard', success='Horario de la encuesta actualizado con éxito.'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        admin_data = load_admin()
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        if old_password == admin_data['password']:
            admin_data['password'] = new_password
            save_admin(admin_data)
            return redirect(url_for('admin_dashboard', success='Contraseña actualizada con éxito.'))
        else:
            flash('Contraseña anterior incorrecta')
    return render_template('change_password.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        admin_data = load_admin()
        if email == admin_data['email']:
            reset_link = url_for('reset_password', _external=True)
            send_reset_email(email, reset_link)
            flash('Se ha enviado un enlace de restablecimiento a su correo electrónico.')
        else:
            flash('Correo electrónico no encontrado.')
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return "Todos los datos personales recabados serán confidenciales y utilizados solo para el control interno de citas."

@app.route('/survey_status')
def survey_status():
    config = load_config()
    return jsonify({'is_open': config['status'] == 'open'})

@app.route('/update_admin_profile', methods=['POST'])
def update_admin_profile():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    email = request.form['email']
    admin_data = load_admin()
    admin_data['email'] = email
    save_admin(admin_data)
    return redirect(url_for('admin_dashboard', success='Perfil del administrador actualizado con éxito.'))

if __name__ == '__main__':
    app.run(debug=True)
