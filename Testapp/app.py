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
    time_parts_count = len(str(time_str).split(":"))
    format_map = {1: '00:00:{}', 2: '00:{}', 3: '{}'}

    if time_parts_count in format_map:
        return pd.to_timedelta(format_map[time_parts_count].format(time_str))
    else:
        raise ValueError(f'Invalid time format: {time_str}')

# Read the CSV file into a DataFrame
df = pd.read_csv('SwimDataTop50.csv')

# Convert 'time' column to timedelta 
df['time'] = df['time'].apply(parse_custom_time)
df['time_seconds'] = df['time'].dt.total_seconds()
df['speed'] = df['distance'] / df['time_seconds']
df["firstname"] = df['firstname'].str.lower()

#Drop duplicatet rows where 'surname', 'firstname', 'distance', 'technique', 'track length' are the same, keep the first row
df = df.drop_duplicates(subset=['surname', 'firstname', 'distance', 'technique', 'track length'], keep='first')

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

# Constants
DISTANCE_200 = 200
TRACK_LENGTHS = ["25", "50"]
TECHNIQUES = ['F', 'R', 'B', 'S', 'L']
TECHNIQUE_MAP = {
    'F': 'Freistil',
    'R': 'Rücken',
    'B': 'Brust',
    'S': 'Schmetterling',
    'L': 'Lagen'
}

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
    firstname = request.args.get('firstname', None).lower()
    lastname = request.args.get('lastname', None).upper()
    track_length = request.args.get('track_length', None)
    technique = request.args.get('technique', None)
    isAbsolute = bool(request.args.get('absolute', False))

    # Validate parameters
    if not firstname or not lastname or not track_length or not technique:
        return 'Invalid request. Please provide all parameters.', 400
    elif technique not in TECHNIQUES:
        return 'Invalid request. Technique must be one of F, R, B, S, L.', 400
    elif track_length not in TRACK_LENGTHS:
        return 'Invalid request. Track length must be one of 25, 50.', 400

    # Lists to store predicted and measured values
    measured_values = []
    predicted_values = []

    # Map the technique
    technique = TECHNIQUE_MAP[technique]

    # Filter the DataFrame based on the provided parameters
    filtered_df = df[(df['firstname'] == firstname) & (df['surname'] == lastname) & (df['track length'] == int(track_length)) & (df['technique'] == technique)]

    # If no data found, return an error message
    if filtered_df.empty:
        return f'No data found for {firstname} {lastname}', 400
    elif len(filtered_df) < 3:
        return f'Not enough data found for {firstname} {lastname}. Only {len(filtered_df)} entrys, 3 needed.', 400
    
    if not isAbsolute:
        # Check if 200m distance is present in the filtered data
        if DISTANCE_200 in filtered_df['distance'].unique():
            # If 200m distance is present, use the speed value for division
            divisor = filtered_df[filtered_df['distance'] == DISTANCE_200]['speed'].values[0]
        else:
            # If 200m distance is not present, find the closest distance and use its speed value for division
            closest_distance_index = (filtered_df['distance'] - 200).abs().argsort().sort_values()[:1].index
            divisor = filtered_df.loc[closest_distance_index, 'speed'].values[0]

        # Calculation for relative speed to 200m
        filtered_df.loc[:,'speed'] = filtered_df['speed'] / divisor


    # Fit a rational function to the filtered data
    params, covariance = curve_fit(fit_rational_function, filtered_df['distance'], filtered_df['speed'], method="dogbox",maxfev=50000)

    x_range = np.linspace(0, 2000, 200)
    y_pred = fit_rational_function(x_range, *params)

    # Create dictionaries for predicted values
    for X, Y in zip(x_range, y_pred):
        predDict = {"x": X, "y": Y}
        predicted_values.append(predDict)

    # Create dictionaries for measured values
    for distance, speed in zip(filtered_df['distance'], filtered_df['speed']):
        mesDict = {"x": distance, "y": speed}
        measured_values.append(mesDict)

    # Create a JSON response containing predicted and measured values
    data = {
        "pred_values": predicted_values,
        "mes_values": measured_values
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


def checker(toCheck, trackLength, technique):
        return technique in toCheck['technique'].values and trackLength in toCheck['track length'].values

@app.route("/possibleOptions")
def possibleOptions():
    # Get parameters from the request URL
    firstname = request.args.get('firstname', None).lower()
    lastname = request.args.get('lastname', None).upper()

    if not firstname or not lastname:
        return 'Invalid request. Please provide all parameters.', 400

    possibleOptions = df[(df['firstname'] == firstname) & (df['surname'] == lastname)]
    grouped_data = possibleOptions.groupby(['surname', 'firstname', 'track length', 'technique'])
    size = grouped_data.size()
    valid = size[size > 2]
    valid = valid.reset_index()

    returnJason = {
        "S-50": checker(valid, 50, 'Schmetterling'),
        "R-50": checker(valid, 50, 'Rücken'),
        "B-50": checker(valid, 50, 'Brust'),
        "F-50": checker(valid, 50, 'Freistil'),
        "L-50": checker(valid, 50, 'Lagen'),
        "S-25": checker(valid, 25, 'Schmetterling'),
        "R-25": checker(valid, 25, 'Rücken'),
        "B-25": checker(valid, 25, 'Brust'),
        "F-25": checker(valid, 25, 'Freistil'),
        "L-25": checker(valid, 25, 'Lagen')
        }
    
    return jsonify(returnJason), 200

# Run the Flask application
if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0', ssl_context=('cert\selfcert.pem', 'cert\selfkey.pem'))