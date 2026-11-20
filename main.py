
from fastapi import FastAPI, HTTPException
import pandas as pd
import joblib

app = FastAPI(
    title="Crop Stress and Irrigation Priority API",
    description="Crop health prediction API",
    version="1.0"
)


model_data = joblib.load("crop_stress_model.pkl")

best_model = model_data["model"]
features = model_data["features"]


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
        input_data = pd.DataFrame(
            [[data[feature] for feature in features]],
            columns=features
        )

        prediction = best_model.predict(input_data)[0]

        probabilities = best_model.predict_proba(input_data)[0]

        class_probabilities = {
            str(label): round(float(probability) * 100, 2)
            for label, probability in zip(
                best_model.classes_,
                probabilities
            )
        }

        return {
            "predicted_crop_condition": str(prediction),
            "confidence_percent": round(
                float(max(probabilities)) * 100, 2
            ),
            "class_probabilities": class_probabilities
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
