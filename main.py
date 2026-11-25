
import os
import json
from pathlib import Path

import pandas as pd
import joblib
import mysql.connector

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Crop Stress and Irrigation Priority API",
    description="Crop health prediction API",
    version="1.0"
)
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

# Load the existing ML model
BASE_DIR = Path(__file__).resolve().parent

model_data = joblib.load(BASE_DIR / "crop_stress_model.pkl")

best_model = model_data["model"]
features = model_data["features"]


# MySQL connection settings
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database="crop_stress_db"
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

    missing_features = [
        feature for feature in features
        if feature not in data
    ]

    if missing_features:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing required features",
                "missing_features": missing_features
            }
        )

    try:
        # Prepare model input
        input_data = pd.DataFrame(
            [[data[feature] for feature in features]],
            columns=features
        )

        # Make prediction
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
            float(max(probabilities)) * 100, 2
        )

        # Save prediction to MySQL
        connection = get_db_connection()
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

        cursor.close()
        connection.close()

        return {
            "predicted_crop_condition": str(prediction),
            "confidence_percent": confidence,
            "class_probabilities": class_probabilities
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



from fastapi import HTTPException
import json


@app.get("/api/history")
def get_prediction_history():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()

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
            if isinstance(record.get("class_probabilities"), str):
                try:
                    record["class_probabilities"] = json.loads(
                        record["class_probabilities"]
                    )
                except json.JSONDecodeError:
                    record["class_probabilities"] = {}

            if record.get("created_at"):
                record["created_at"] = str(record["created_at"])

        return {"records": records}

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
