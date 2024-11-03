from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)

# Replace with your actual OpenWeatherMap API key
GEOCODING_API_KEY = "aed05528d555dbb50a948b41b2387806"

def get_coordinates(city):
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={GEOCODING_API_KEY}"
    response = requests.get(geocode_url)
    data = response.json()
    print(f"Geocoding response for {city}: {data}")  # Debugging output

    # Check if the response has an error message
    if 'cod' in data and data['cod'] == 401:
        print("Invalid API Key error.")
        return None, None
    
    # Check if data is valid and contains location information
    if data and len(data) > 0:
        latitude = data[0].get('lat')
        longitude = data[0].get('lon')
        return latitude, longitude
    else:
        return None, None  # Return None if the city is not found

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        city = request.form['city']
        return redirect(url_for('weather', city=city))
    return render_template('index.html')

@app.route('/weather/<city>')
def weather(city):
    # Get dynamic coordinates for the city
    latitude, longitude = get_coordinates(city)
    
    if latitude is None or longitude is None:
        # Display an error message if the city coordinates couldn't be retrieved
        return f"Could not find coordinates for {city}. Please check the city name and try again.", 404

    # Use the obtained coordinates to fetch weather and UV data
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,uv_index"
    response = requests.get(api_url)
    data = response.json()

    # Check if 'hourly' data is available in the response
    if 'hourly' in data and 'uv_index' in data['hourly'] and 'temperature_2m' in data['hourly']:
        uv_data = data['hourly']['uv_index'][:24]  # Get the first 24 hours of UV index data
        temp_data = data['hourly']['temperature_2m'][:24]  # Get the first 24 hours of temperature data
        labels = [f"Hour {i+1}" for i in range(24)]
    else:
        # Provide empty data and labels if 'hourly' key or data is missing
        uv_data = []
        temp_data = []
        labels = []

    # Prepare weather information for display
    weather_info = {
        'temperature': temp_data[0] if temp_data else "N/A",
        'uv_index': uv_data[0] if uv_data else "N/A",
        'city': city
    }

    # Categorize the UV index if available, else set to "Unknown"
    uv_category = categorize_uv_index(weather_info['uv_index']) if uv_data else "Unknown"

    return render_template('weather.html', weather_info=weather_info, uv_category=uv_category, uv_data=uv_data, temp_data=temp_data, labels=labels)

def categorize_uv_index(uv_index):
    """Categorize UV index into risk levels."""
    if uv_index == "N/A":
        return "Unknown"
    elif uv_index < 3:
        return 'Low'
    elif uv_index < 6:
        return 'Moderate'
    elif uv_index < 8:
        return 'High'
    elif uv_index < 11:
        return 'Very High'
    else:
        return 'Extreme'

if __name__ == '__main__':
    app.run(debug=True)