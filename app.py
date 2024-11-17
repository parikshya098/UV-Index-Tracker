from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import requests
import smtplib
from datetime import datetime
from flask_cors import CORS
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'saana2003'
CORS(app, resources={r"/*": {"origins": "*"}})

EMAIL_ADDRESS = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASS')

# API Key for Geoapify (used for reverse geocoding)
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

def send_email(to_email, subject, body):
    """Send an email using SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")

def get_coordinates(location):
    """Fetch coordinates using Open-Meteo Geocoding API."""
    try:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        response = requests.get(geocode_url)
        response.raise_for_status()
        data = response.json()
        if 'results' in data and data['results']:
            latitude = data['results'][0]['latitude']
            longitude = data['results'][0]['longitude']
            return latitude, longitude
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching coordinates: {e}")
        return None, None

def get_weather_data(latitude, longitude, start_date, end_date):
    """Fetch weather data including UV index using Open-Meteo API."""
    try:
        api_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&"
            f"hourly=uv_index,temperature_2m&start_date={start_date}&end_date={end_date}&timezone=auto"
        )
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    location = request.form.get('location')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')

    # Validate form inputs
    if not location or not from_date or not to_date:
        flash("Please enter a location and valid date range.", "error")
        return redirect(url_for('index'))

    # Fetch coordinates for the location
    latitude, longitude = get_coordinates(location)
    if not latitude or not longitude:
        flash("Could not find coordinates for the location.", "error")
        return redirect(url_for('index'))

    # Redirect to the weather route with the query parameters
    return redirect(url_for(
        'weather',
        city=location,
        latitude=latitude,
        longitude=longitude,
        from_date=from_date,
        to_date=to_date
    ))

@app.route('/weather')
def weather():
    city = request.args.get('city')
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not city or not latitude or not longitude or not from_date or not to_date:
        flash("Invalid or missing query parameters.", "error")
        return redirect(url_for('index'))

    weather_data = get_weather_data(latitude, longitude, from_date, to_date)
    if not weather_data:
        flash("Error fetching weather data.", "error")
        return redirect(url_for('index'))

    uv_data = weather_data.get('hourly', {}).get('uv_index', [])
    time_data = weather_data.get('hourly', {}).get('time', [])

    # Fetch country using reverse geocoding
    geo_response = requests.get(f"http://127.0.0.1:8000/reverse-geocode?latitude={latitude}&longitude={longitude}")
    geo_data = geo_response.json()
    country = geo_data.get('country', 'Unknown Country')

    weather_info = {
        'city': city,
        'country': country,  # Add this line
        'latitude': latitude,
        'longitude': longitude,
        'from_date': from_date,
        'to_date': to_date,
        'uv_data': uv_data,
        'time_data': time_data,
        'uv_index': uv_data[-1] if uv_data else None
    }

    return render_template('weather.html', weather_info=weather_info)

@app.route('/reverse-geocode')
def reverse_geocode():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    
    if not latitude or not longitude:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        geo_url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latitude}&lon={longitude}&apiKey={GEOAPIFY_API_KEY}"
        response = requests.get(geo_url)
        response.raise_for_status()
        data = response.json()
        if 'features' in data and data['features']:
            city = data['features'][0]['properties'].get('city', 'Unknown City')
            country = data['features'][0]['properties'].get('country', 'Unknown Country')
            return jsonify({"city": city, "country": country})
        return jsonify({"error": "No city found"}), 404
    except requests.exceptions.RequestException as e:
        print(f"Error during reverse geocoding: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        user_email = request.form.get('email')

        if feedback_text:
            # Send feedback to your email
            send_email(
                to_email=EMAIL_ADDRESS,
                subject="New Feedback Received",
                body=f"Feedback: {feedback_text}\nFrom: {user_email if user_email else 'Anonymous'}"
            )
            flash("Thank you for your feedback!", "success")
        else:
            flash("Please provide your feedback.", "error")

        return redirect(url_for('feedback'))
    return render_template('feedback.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_email = request.form.get('contact_info')

        if user_email:
            # Send a thank you email to the user
            send_email(
                to_email=user_email,
                subject="Thank you for signing up!",
                body="Thanks for signing up for UV Index Alerts! You'll receive alert notifications on high UV index days."
            )
            flash("Successfully signed up for alerts!", "success")
        else:
            flash("Please enter a valid email.", "error")

        return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True)