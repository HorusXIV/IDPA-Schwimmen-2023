from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit

# Create a Flask web application
app = Flask(__name__)
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

# Define a function to plot the rational function fit
def plot_rational_function(distance, speed, ax, title):
    file=open('y_points.txt','w')
    params, covariance = curve_fit(fit_rational_function, distance, speed, method="dogbox")

    x_range = np.linspace(0, 2000, 200)
    y_pred = fit_rational_function(x_range, *params)

    for number in speed:
        file.write(str(number)+",")

    ax.scatter(distance, speed, color='blue', label='Data')
    ax.plot(x_range, y_pred, color='red', label='Rational Function Fit')
    ax.set_title(title)
    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('Speed (m/s)')
    ax.set_ylim(y_pred.min()-0.1, y_pred.max()+0.1)  # Set y-axis limits
    ax.legend()
    


# Define a route for the web application
@app.route('/requestData')
def plot_rational_function_for_swimmer():
    # Get parameters from the request URL
    firstname = request.args.get('firstname', None)
    lastname = request.args.get('lastname', None)
    track_length = request.args.get('track_length', None)
    technique = request.args.get('technique', None)

    values = {}
    returndict = {}

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
        return f'No data found for {firstname} {lastname}.'
    
    # Fit a rational function to the filtered data
    params, covariance = curve_fit(fit_rational_function, filtered_df['distance'], filtered_df['speed'], method="dogbox")

    x_range = np.linspace(0, 2000, 200)
    y_pred = fit_rational_function(x_range, *params)

    # Create dictionaries for predicted and measured values
    for X, Y in zip(x_range, y_pred):
        returndict[X] = Y

    for distance, speed in zip(filtered_df['distance'], filtered_df['speed']):
        values[distance] = speed

    # Create a JSON response containing predicted and measured values
    data = {
        "pred_values": returndict,
        "mes_values": values
    }
    return jsonify(data)

# Run the Flask application
if __name__ == '__main__':
   app.run(debug = True, port=9387, host='0.0.0.0', ssl_context=('adhoc'))