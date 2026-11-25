
import os
import json
from pathlib import Path

import pandas as pd
import joblib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Crop Stress and Irrigation Priority API",
    description="Crop health prediction API",
    version="1.0"
)

# Allow your local frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained ML model
BASE_DIR = Path(__file__).resolve().parent

model_data = joblib.load(BASE_DIR / "crop_stress_model.pkl")

best_model = model_data["model"]
features = model_data["features"]


# MySQL is optional.
# Render will not use localhost as a database server.
def get_db_connection():
    db_host = os.getenv("DB_HOST")

    if not db_host:
        return None

    import mysql.connector

    return mysql.connector.connect(
        host=db_host,
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "crop_stress_db"),
        port=int(os.getenv("DB_PORT", "3306")),
        connection_timeout=10
    )


@app.get("/")
def home():
    return {
        "message": "Crop Stress API is running successfully"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": True
    }


@app.post("/predict")
def predict(data: dict):

    # Check whether all trained model features were supplied
    missing_features = [
        feature for feature in features
        if feature not in data
    ]

    if missing_features:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing required model features",
                "missing_features": missing_features
            }
        )

    try:
        # Prepare input in the exact training feature order
        input_data = pd.DataFrame(
            [[data[feature] for feature in features]],
            columns=features
        )

        # Predict crop condition
        prediction = best_model.predict(input_data)[0]

        probabilities = best_model.predict_proba(input_data)[0]

        class_probabilities = {
            str(label): round(float(probability) * 100, 2)
            for label, probability in zip(
                best_model.classes_,
                probabilities
            )
        }

        confidence = round(
            float(max(probabilities)) * 100,
            2
        )

    except Exception as error:
        print("Prediction error:", error)

        raise HTTPException(
            status_code=500,
            detail="The ML model could not make a prediction."
        )

    # Database saving is optional.
    # A database error must not prevent the model prediction.
    saved_to_database = False

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection:
            cursor = connection.cursor()

            insert_query = """
                INSERT INTO prediction_records (
                    village,
                    district,
                    state,
                    field_id,
                    crop,
                    growth_stage,
                    season,
                    soil_moisture,
                    model_inputs,
                    weather_data,
                    crop_condition,
                    confidence_percent,
                    class_probabilities,
                    recommendation
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """

            values = (
                data.get("village"),
                data.get("district"),
                data.get("state"),
                data.get("field_id"),
                data.get("crop"),
                data.get("growth_stage"),
                data.get("season"),
                data.get("soil_moisture"),
                json.dumps({
                    feature: data[feature]
                    for feature in features
                }),
                json.dumps(data.get("weather_data", {})),
                str(prediction),
                confidence,
                json.dumps(class_probabilities),
                data.get("recommendation")
            )

            cursor.execute(insert_query, values)
            connection.commit()

            saved_to_database = True

    except Exception as error:
        print("Database save error:", error)

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

    # Return prediction even if database is unavailable
    return {
        "predicted_crop_condition": str(prediction),
        "confidence_percent": confidence,
        "class_probabilities": class_probabilities,
        "saved_to_database": saved_to_database
    }


@app.get("/api/history")
def get_prediction_history():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        # No cloud database configured yet
        if connection is None:
            return {
                "records": [],
                "message": "Database is not configured. History storage is unavailable."
            }

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                prediction_id,
                village,
                district,
                state,
                field_id,
                crop,
                growth_stage,
                season,
                crop_condition,
                confidence_percent,
                class_probabilities,
                risk_score,
                risk_level,
                insurance_risk_score,
                irrigation_priority,
                recommendation,
                created_at
            FROM prediction_records
            ORDER BY prediction_id DESC
            LIMIT 100
        """)

        records = cursor.fetchall()

        for record in records:
            probabilities = record.get("class_probabilities")

            if isinstance(probabilities, str):
                try:
                    record["class_probabilities"] = json.loads(
                        probabilities
                    )
                except json.JSONDecodeError:
                    record["class_probabilities"] = {}

            if record.get("created_at"):
                record["created_at"] = str(
                    record["created_at"]
                )

        return {
            "records": records,
            "message": "Prediction history loaded successfully."
        }

    except Exception as error:
        print("History error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not load prediction history."
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
