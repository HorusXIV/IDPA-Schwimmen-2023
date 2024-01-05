from flask import Flask, request, jsonify
from scipy.optimize import curve_fit
import pandas as pd
import numpy as np

# Create a Flask web application
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev'
)

# Function to parse time strings with variable formats
def parse_custom_time(time_str):
    format = len(str(time_str).split(":"))

    if format == 1:
        return pd.to_timedelta(f'00:00:{time_str}')
    elif format == 2:
        return pd.to_timedelta(f'00:{time_str}')
    elif format == 3:
        return pd.to_timedelta(time_str)

# Read the CSV file into a DataFrame
df = pd.read_csv('SwimDataTop50.csv')

# Convert 'time' column to timedelta 
df['time'] = df['time'].apply(parse_custom_time)
df['time_seconds'] = df['time'].dt.total_seconds()
df['speed'] = df['distance'] / df['time_seconds']

# Group the data by 'surname', 'firstname', 'track length', 'technique'
grouped_data = df.groupby(['surname', 'firstname', 'track length', 'technique'])

# Define a rational function for curve fitting
def fit_rational_function(x, a, b, c):
    return 1 / (a * x + b) + c  

# Define a route for the web application
@app.route('/requestData')
def plot_rational_function_for_swimmer():
    # Get parameters from the request URL
    firstname = request.args.get('firstname', None)
    lastname = request.args.get('lastname', None).upper()
    track_length = request.args.get('track_length', None)
    technique = request.args.get('technique', None)

    if not firstname or not lastname or not track_length or not technique:
        return 'Invalid request. Please provide all parameters.', 400
    elif not technique in ['F', 'R', 'B', 'S', 'L']:
        return 'Invalid request. Technique must be one of F, R, B, S, L.', 400
    elif not track_length in ["25", "50"]:
        return 'Invalid request. Track length must be one of 25, 50.', 400
    
    mesList = []
    predList = []

    # Mapping for swimming techniques
    map = {
        'F': 'Freistil',
        'R': 'Rücken',
        'B': 'Brust',
        'S': 'Schmetterling',
        'L': 'Lagen'
    }

    # Map the technique
    technique = map[technique]
 
    # Filter the DataFrame based on the provided parameters
    filtered_df = df[(df['firstname'] == firstname) & (df['surname'] == lastname) & (df['track length'] == int(track_length)) & (df['technique'] == technique)]

    # If no data found, return a message
    if filtered_df.empty:
        return f'No data found for {firstname} {lastname}.', 400
    elif len(filtered_df) < 3:
        return f'Not enough data found for {firstname} {lastname}.', 400
    
    # Fit a rational function to the filtered data
    params, covariance = curve_fit(fit_rational_function, filtered_df['distance'], filtered_df['speed'])

    x_range = np.linspace(0, 2000, 200)
    y_pred = fit_rational_function(x_range, *params)

    # Create dictionaries for predicted and measured values
    for X, Y in zip(x_range, y_pred):
        predDict = {"x": X, "y": Y}
        predList.append(predDict)

    for distance, speed in zip(filtered_df['distance'], filtered_df['speed']):
        mesDict = {"x": distance, "y": speed}
        mesList.append(mesDict)

    # Create a JSON response containing predicted and measured values
    data = {
        "pred_values": predList,
        "mes_values": mesList
    }
    return jsonify(data), 200


@app.route('/swimmers')
def getAllSwimmers():
    swimmers = []
    uniquedf = df[['firstname', 'surname']].drop_duplicates()
    # Get all unique swimmers
    for firstname, lastname in zip(uniquedf['firstname'], uniquedf['surname']):
        swimmers.append(firstname + ' ' + lastname)

    return jsonify(swimmers)

# Run the Flask application
if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0', ssl_context=('cert\selfcert.pem', 'cert\selfkey.pem'))
   