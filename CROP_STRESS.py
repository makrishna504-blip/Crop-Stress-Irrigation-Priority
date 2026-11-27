







import pandas as pd
import requests

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

import warnings
warnings.filterwarnings("ignore")
df = pd.read_csv("final_crop_stress_dataset.csv")

print("Dataset shape:", df.shape)
print(df.head())
print(df["category"].value_counts())




df.columns = df.columns.str.strip()
df = df.dropna(subset=["category"])

df["SDate"] = pd.to_datetime(df["SDate"], errors="coerce")
df["HDate"] = pd.to_datetime(df["HDate"], errors="coerce")
df["crop_duration_days"] = (df["HDate"] - df["SDate"]).dt.days


X = df.drop(columns=["category", "FarmID", "SDate", "HDate","State","District","Sub-District","CropCoveredArea","CHeight","ExpYield","longitude","latitude","season_weather_days"], errors="ignore")
y = df["category"]


X = pd.get_dummies(X)
X = X.fillna(X.median())

print("Data is ready for training.")




X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


rf_model = RandomForestClassifier(
    class_weight="balanced",
    random_state=42
)


param_grid = {
    "n_estimators": [100, 200],
    "max_depth": [None, 10, 20],
    "min_samples_split": [2, 5],
    "min_samples_leaf": [1, 2],
    "max_features": ["sqrt", "log2"]
}

grid_search = GridSearchCV(
    estimator=rf_model,
    param_grid=param_grid,
    cv=5,
    scoring="f1_weighted",
    n_jobs=-1,
    verbose=1
)

grid_search.fit(X_train, y_train)

model = grid_search.best_estimator_

print("Hyperparameter tuning completed!")
print("Best parameters:", grid_search.best_params_)

print("Best Cross Validation Score:",
      round(grid_search.best_score_, 4))

print("Model training completed!")



predictions = model.predict(X_test)

print("Accuracy:", round(accuracy_score(y_test, predictions) * 100, 2), "%")
print(classification_report(y_test, predictions, zero_division=0))




def get_risk_level(score):
    if score <= 25:
        return "Low"
    elif score <= 50:
        return "Moderate"
    elif score <= 75:
        return "High"
    else:
        return "Critical"


def get_recommendation(level):
    if level == "Low":
        return "Continue regular monitoring."
    elif level == "Moderate":
        return "Monitor crop conditions."
    elif level == "High":
        return "Prioritize field inspection."
    else:
        return "Urgent field inspection required."


import requests

def get_weather(village):

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": village,
        "count": 5,
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    if not data.get("results"):
        raise ValueError("Invalid location! Please enter a valid village name.")

    place = data["results"][0]

    location_name = place["name"]

    print("Location found:", location_name)
    print("State:", place.get("admin1", "Unknown"))
    print("Country:", place.get("country", "Unknown"))

    confirm = input("Is this your correct location? (yes/no): ")

    if confirm.lower() != "yes":
        raise ValueError("Location not confirmed. Prediction stopped.")

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "daily": [
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "soil_moisture_0_to_7cm_mean",
            "soil_moisture_7_to_28cm_mean"
        ],
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "auto"
    }

    weather_response = requests.get(weather_url, params=weather_params)
    weather_response.raise_for_status()

    weather_data = weather_response.json()

    return weather_data, location_name



village = input("Enter village name: ")
district = input("Enter district: ")
state = input("Enter state: ")
crop = input("Enter crop name: ")
season = input("Enter season (Kharif/Rabi): ")


weather_data, location_name = get_weather(village)

print("Location found:", location_name)
daily = weather_data["daily"]

weather_df = pd.DataFrame(daily)

print(weather_df)


new_farm = df.drop(columns=["category", "FarmID", "SDate", "HDate"], errors="ignore").iloc[[0]].copy()

new_farm["Crop"] = crop
new_farm["Season"] = season
new_farm["State"] = state
new_farm["District"] = district


for column, value in weather_data.items():
    if column in new_farm.columns:
        new_farm[column] = value


new_farm = pd.get_dummies(new_farm)
new_farm = new_farm.reindex(columns=X.columns, fill_value=0)
new_farm = new_farm.fillna(X.median())



predicted_condition = model.predict(new_farm)[0]
probabilities = model.predict_proba(new_farm)[0]

class_names = model.classes_
probability = dict(zip(class_names, probabilities))

healthy_probability = probability.get("Healthy", 0)
stressed_probability = probability.get("Stressed", 0)

# Calculate crop risk
risk_score = (1 - healthy_probability) * 100
risk_level = get_risk_level(risk_score)

daily = weather_data["daily"]

soil_moisture = daily["soil_moisture_0_to_7cm_mean"]

valid_moisture = [x for x in soil_moisture if x is not None]

if valid_moisture:
    avg_moisture = sum(valid_moisture) / len(valid_moisture)
else:
    avg_moisture = None

stress_probability = stressed_probability * 100

if avg_moisture is None:
    if stress_probability >= 50:
        irrigation_priority = "High"
    elif stress_probability >= 25:
        irrigation_priority = "Medium"
    else:
        irrigation_priority = "Low"

elif stress_probability >= 50 or avg_moisture < 0.15:
    irrigation_priority = "High"

elif stress_probability >= 25 or avg_moisture < 0.25:
    irrigation_priority = "Medium"

else:
    irrigation_priority = "Low"


print("\n===== CROP RISK AND IRRIGATION REPORT =====")

print("Village:", village)
print("Crop:", crop)

print("\n--- CROP RISK DETAILS ---")
print("Predicted crop condition:", predicted_condition)
print("Stressed probability:", round(stress_probability, 2), "%")
print("Insurance monitoring risk score:", round(risk_score, 2), "%")
print("Risk level:", risk_level)
print("Recommended action:", get_recommendation(risk_level))

print("\n--- IRRIGATION DETAILS ---")

if avg_moisture is not None:
    print("Average Soil Moisture:", round(avg_moisture, 3))
else:
    print("Average Soil Moisture: Not available")

print("Irrigation Priority:", irrigation_priority)

if irrigation_priority == "High":
    print("Irrigation Recommendation: Give irrigation priority to this field.")

elif irrigation_priority == "Medium":
    print("Irrigation Recommendation: Monitor soil moisture and plan irrigation.")

else:
    print("Irrigation Recommendation: No immediate irrigation priority.")

print("\n--- CLASS PROBABILITIES ---")

for name, value in probability.items():
    print(name, ":", round(value * 100, 2), "%")





import joblib

joblib.dump(
    {
        "model": model,
        "features": X.columns.tolist()
    },
    "crop_stress_model.pkl"
)

print("Crop Stress Model saved successfully!")






