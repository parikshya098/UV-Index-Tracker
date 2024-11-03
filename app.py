from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        city = request.form['city']
        return redirect(url_for('weather', city=city))
    return render_template('index.html')

@app.route('/weather/<city>')
def weather(city):
    # Example coordinates for testing
    latitude = 34.7465
    longitude = -92.2896

    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,uv_index"
    response = requests.get(api_url)
    data = response.json()

    weather_info = {
        'temperature': data['hourly']['temperature_2m'][0],
        'uv_index': data['hourly']['uv_index'][0],
    }

    uv_category = categorize_uv_index(weather_info['uv_index'])
    return render_template('weather.html', weather_info=weather_info, uv_category=uv_category)

def categorize_uv_index(uv_index):
    if uv_index < 3:
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