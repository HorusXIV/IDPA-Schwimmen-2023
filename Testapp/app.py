from flask import Flask, request, jsonify
from scipy.optimize import curve_fit
import pandas as pd
import numpy as np

# Create a Flask web application
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev'
)

def parse_custom_time(time_str):
    """
    Parse time strings with variable formats.

    Parameters:
    - time_str (str): A string representing time in one of the following formats:
        - Seconds only
        - Minutes:Seconds
        - Hours:Minutes:Seconds

    Returns:
    - pd.Timedelta: A Pandas Timedelta object representing the parsed time.

    Raises:
    - ValueError: If the input time string does not match any of the expected formats.
    """
    # Determine the format of the input time string
    num_segments = len(str(time_str).split(":"))

    # Parse the time string based on the detected format
    if num_segments == 1:
        # Seconds only format
        return pd.to_timedelta(f'00:00:{time_str}')
    elif num_segments == 2:
        # Minutes:Seconds format
        return pd.to_timedelta(f'00:{time_str}')
    elif num_segments == 3:
        # Hours:Minutes:Seconds format
        return pd.to_timedelta(time_str)
    else:
        # Raise an error for unexpected formats
        raise ValueError("Invalid time string format. Expected one of: Seconds, Minutes:Seconds, Hours:Minutes:Seconds.")

# Read the CSV file into a DataFrame
df = pd.read_csv('SwimDataTop50.csv')

# Convert 'time' column to timedelta 
df['time'] = df['time'].apply(parse_custom_time)
df['time_seconds'] = df['time'].dt.total_seconds()
df['speed'] = df['distance'] / df['time_seconds']

# Group the data by 'surname', 'firstname', 'track length', 'technique'
grouped_data = df.groupby(['surname', 'firstname', 'track length', 'technique'])

def fit_rational_function(x, a, b, c):
    """
    Define a rational function for curve fitting.

    Parameters:
    - x (array-like): Input values for the rational function.
    - a (float): Coefficient for the x term in the denominator.
    - b (float): Coefficient for the constant term in the denominator.
    - c (float): Constant term in the numerator.

    Returns:
    - array-like: Output values of the rational function for the given input.

    Note:
    The rational function is defined as 1 / (a * x + b) + c.
    """
    # Calculate the output values of the rational function
    return 1 / (a * x + b) + c

# Define a route for the web application
@app.route('/requestData')
def plot_rational_function_for_swimmer():
    """
    Endpoint to retrieve swimming data for a specific swimmer and plot the rational function fit.

    Returns:
    - JSON: A JSON response containing both predicted and measured speed values for various distances.
    - HTTP Status Code 200: Successful response.
    - HTTP Status Code 400: Invalid request or insufficient data found.
    """
    # Get parameters from the request URL
    firstname = request.args.get('firstname', None)
    lastname = request.args.get('lastname', None).upper()
    track_length = request.args.get('track_length', None)
    technique = request.args.get('technique', None)

    # Validate parameters
    if not firstname or not lastname or not track_length or not technique:
        return 'Invalid request. Please provide all parameters.', 400
    elif technique not in ['F', 'R', 'B', 'S', 'L']:
        return 'Invalid request. Technique must be one of F, R, B, S, L.', 400
    elif track_length not in ["25", "50"]:
        return 'Invalid request. Track length must be one of 25, 50.', 400

    # Lists to store predicted and measured values
    mesList = []
    predList = []

    # Mapping for swimming techniques
    technique_map = {
        'F': 'Freistil',
        'R': 'Rücken',
        'B': 'Brust',
        'S': 'Schmetterling',
        'L': 'Lagen'
    }

    # Map the technique
    technique = technique_map[technique]

    # Filter the DataFrame based on the provided parameters
    filtered_df = df[(df['firstname'] == firstname) & (df['surname'] == lastname) & (df['track length'] == int(track_length)) & (df['technique'] == technique)]

    # If no data found, return an error message
    if filtered_df.empty:
        return f'No data found for {firstname} {lastname}.', 400
    elif len(filtered_df) < 3:
        return f'Not enough data found for {firstname} {lastname}.', 400

    # Fit a rational function to the filtered data
    params, covariance = curve_fit(fit_rational_function, filtered_df['distance'], filtered_df['speed'])

    x_range = np.linspace(0, 2000, 200)
    y_pred = fit_rational_function(x_range, *params)

    # Create dictionaries for predicted values
    for X, Y in zip(x_range, y_pred):
        predDict = {"x": X, "y": Y}
        predList.append(predDict)

    # Create dictionaries for measured values
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
    """
    Endpoint to retrieve a list of all unique swimmers.

    Returns:
    - JSON: A JSON response containing a list of all unique swimmers.
    """
    swimmers = []

    # Extract unique combinations of 'firstname' and 'surname' from the DataFrame
    uniquedf = df[['firstname', 'surname']].drop_duplicates()

    # Get all unique swimmers
    for firstname, lastname in zip(uniquedf['firstname'], uniquedf['surname']):
        swimmers.append(firstname + ' ' + lastname)

    # Return the list of unique swimmers as JSON
    return jsonify(swimmers)

# Run the Flask application
if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0', ssl_context=('cert\selfcert.pem', 'cert\selfkey.pem'))
   