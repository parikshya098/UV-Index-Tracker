from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'saana2003'

GEOCODING_API_KEY = "aed05528d555dbb50a948b41b2387806"

def get_coordinates(location):
    if location.isdigit():
        geocode_url = f"http://api.openweathermap.org/geo/1.0/zip?zip={location},US&appid={GEOCODING_API_KEY}"
    else:
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={GEOCODING_API_KEY}"
    
    response = requests.get(geocode_url)
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

def get_weather_data(latitude, longitude):
    api_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&"
        "current=temperature_2m,relative_humidity_2m,uv_index&"
        "hourly=uv_index&daily=uv_index_max&timezone=auto"
    )
    response = requests.get(api_url)
    return response.json()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            return redirect(url_for('weather', location=location))
        else:
            return "Location field is required.", 400
    return render_template('index.html')

@app.route('/weather/<location>')
def weather(location):
    latitude, longitude = get_coordinates(location)
    
    if latitude is None or longitude is None:
        return f"Could not find coordinates for {location}. Please check the location name or ZIP code and try again.", 404

    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m&hourly=uv_index&daily=uv_index_max&timezone=auto&past_days=7&past_hours=24&forecast_hours=24"
    response = requests.get(api_url)
    data = response.json()

    # Safely retrieve data or default to empty lists
    temp_data = data.get('hourly', {}).get('temperature_2m', [None] * 24)
    uv_data = data.get('hourly', {}).get('uv_index', [None] * 24)
    hourly_labels = data.get('hourly', {}).get('time', [None] * 24)
    
    # Safely get current data
    weather_info = {
        'temperature': temp_data[0] if temp_data else "N/A",
        'humidity': data.get('current', {}).get('relative_humidity_2m', "N/A"),
        'uv_index': uv_data[0] if uv_data else "N/A",
        'city': location
    }

    return render_template(
        'weather.html',
        weather_info=weather_info,
        temp_data=temp_data,
        uv_data=uv_data,
        hourly_labels=hourly_labels,
        hourly_uv_data=zip(hourly_labels, uv_data)
    )

# Feedback route to display the feedback form page
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback = request.form.get('feedback')
        email = request.form.get('email')
        
        # Process the feedback, e.g., save it to a file or print to console (for demo purposes)
        print("Feedback received:", feedback)
        if email:
            print("User email:", email)

        # Show a success message after submission
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('feedback'))
    
    return render_template('feedback.html')

# Route to handle the feedback form submission specifically (optional)
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    feedback = request.form.get('feedback')
    email = request.form.get('email')
    
    # Process the feedback here (e.g., log to console or save to file)
    print("Feedback submitted:", feedback)
    if email:
        print("User email:", email)
    
    flash("Thank you for your feedback!", "success")
    return redirect(url_for('feedback'))

# Route for signup alert (existing route)
@app.route('/signup-alert', methods=['POST'])
def signup_alert():
    contact_info = request.form.get('contact_info')
    # Process notification signup (e.g., add to mailing list)
    print("User signed up for alerts:", contact_info)
    flash("You have signed up for UV Index alerts.", "success")
    return redirect(url_for('feedback'))

if __name__ == '__main__':
    app.run(debug=True)