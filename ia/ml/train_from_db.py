import pandas as pd
from django.db import connections
from ia.ml.feature_extraction import extract_column_features
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import os
from db_connection_app.utils import register_dynamic_db



BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "column_data_from_db.csv")

def collect_training_data(db_alias):
    all_rows = []

    connection = connections[db_alias]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        try:
            df_features = extract_column_features(
                table_name=table,
                db_alias=db_alias
            )

            df_features["table_name"] = table
            df_features["semantic_type"] = ""  # À remplir manuellement

            all_rows.append(df_features)

        except Exception as e:
            print(f"❌ {table}: {e}")

    df = pd.concat(all_rows, ignore_index=True)
    df.to_csv(DATASET_PATH, index=False)
    print("Dataset généré :", DATASET_PATH)
