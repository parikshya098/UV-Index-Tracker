from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
from datetime import datetime
from flask_cors import CORS
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'saana2003'
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'
mail = Mail(app)

# API keys for geocoding and weather data
GEOCODING_API_KEY = "aed05528d555dbb50a948b41b2387806"
GEOAPIFY_API_KEY = "762a915c41de446e9484044f0ac7c6b4"

@app.after_request
def apply_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https://api.open-meteo.com https://api.geoapify.com;"
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

def get_coordinates(location):
    """Fetch coordinates based on city name or ZIP code."""
    try:
        if location.isdigit():
            geocode_url = f"http://api.openweathermap.org/geo/1.0/zip?zip={location},US&appid={GEOCODING_API_KEY}"
        else:
            geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={GEOCODING_API_KEY}"
        
        response = requests.get(geocode_url)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and data:
            latitude = data[0].get('lat')
            longitude = data[0].get('lon')
        elif 'lat' in data and 'lon' in data:
            latitude = data.get('lat')
            longitude = data.get('lon')
        else:
            return None, None
        return latitude, longitude
    except requests.exceptions.RequestException as e:
        print(f"Error fetching coordinates: {e}")
        return None, None

def get_weather_data(latitude, longitude, start_date, end_date):
    """Fetch weather data including UV index and temperature."""
    try:
        api_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&"
            f"hourly=uv_index,temperature_2m&start_date={start_date}&end_date={end_date}&timezone=auto"
        )
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        return data if 'hourly' in data else {'hourly': {'uv_index': [], 'temperature_2m': [], 'time': []}}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return {'hourly': {'uv_index': [], 'temperature_2m': [], 'time': []}}

@app.route('/reverse-geocode')
def reverse_geocode():
    """Fetch city name based on latitude and longitude."""
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    if not latitude or not longitude:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        geo_url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latitude}&lon={longitude}&apiKey={GEOAPIFY_API_KEY}"
        response = requests.get(geo_url)
        response.raise_for_status()
        data = response.json()

        if data.get('features'):
            city = data['features'][0]['properties'].get('city', 'Unknown City')
            return jsonify({"city": city})
        else:
            return jsonify({"error": "No city found"}), 404
    except requests.exceptions.RequestException as e:
        print(f"Error during reverse geocoding: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        location = request.form.get('location')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')

        if not from_date or not to_date:
            flash("Please select a valid date range.", "error")
            return render_template('index.html')

        if not location and not (latitude and longitude):
            flash("Please enter a location or coordinates.", "error")
            return render_template('index.html')

        if location and not (latitude and longitude):
            latitude, longitude = get_coordinates(location)

        if not latitude or not longitude:
            flash(f"Could not find coordinates for {location}.", "error")
            return render_template('index.html')

        return redirect(url_for(
            'weather', 
            city=location, 
            latitude=latitude, 
            longitude=longitude, 
            from_date=from_date, 
            to_date=to_date
        ))

    return render_template('index.html')


@app.route('/weather')
def weather():
    city = request.args.get('city', 'Unknown City')
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not latitude or not longitude or not from_date or not to_date:
        flash("Invalid or missing query parameters.", "error")
        return redirect(url_for('index'))

    # Fetch the weather data
    data = get_weather_data(latitude, longitude, from_date, to_date)

    uv_data = data.get('hourly', {}).get('uv_index', [])
    time_data = data.get('hourly', {}).get('time', [])

    # Get the current UV index value
    current_uv_index = uv_data[0] if uv_data else None

    weather_info = {
        'city': city,
        'latitude': latitude,
        'longitude': longitude,
        'from_date': from_date,
        'to_date': to_date,
        'uv_index': current_uv_index
    }

    print("Fetched UV Data:", uv_data)
    print("Fetched Time Data:", time_data)

    return render_template(
        'weather.html',
        weather_info=weather_info,
        uv_data=uv_data,
        time_data=time_data
    )

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        user_feedback = request.form.get('feedback')
        email = request.form.get('email')

        # Check if feedback was provided
        if user_feedback:
            print(f"Feedback received: {user_feedback}")
            if email:
                print(f"User email: {email}")
            flash("Thank you for your feedback!", "success")
        else:
            flash("Please enter your feedback before submitting.", "error")
        
        return redirect(url_for('feedback'))
    
    return render_template('feedback.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('contact_info')

        # Validate email input
        if email:
            print(f"Signup received: {email}")
            flash("Successfully signed up for UV index alerts!", "success")
            
            # # Send confirmation email
            # send_confirmation_email(email)
        else:
            flash("Please enter a valid email address.", "error")
        
        return redirect(url_for('signup'))
    
    return render_template('signup.html')

# def send_confirmation_email(user_email):
#     """Send a confirmation email using SendGrid."""
#     message = Mail(
#         from_email='aa@example.edu',
#         to_emails=user_email,
#         subject='Thank You for Signing Up for UV Index Alerts',
#         plain_text_content="""
#         Thank you for signing up for UV index alerts!
#         You will receive notifications on high UV index days, especially helpful for sensitive skin.
        
#         Stay safe and protected!
#         """
#     )

#     try:
#         sg = SendGridAPIClient('api_key')
#         response = sg.send(message)
#         print(f"Email sent to {user_email}")
#     except Exception as e:
#         print(f"Failed to send email: {e}")

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

if __name__ == '__main__':
    app.run(port=5001, debug=True)