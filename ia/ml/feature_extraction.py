import pandas as pd
from django.db import connections

def extract_column_features(
    table_name,
    db_alias,
    limit=1000
):
    """
    UNE LIGNE = UNE COLONNE
    Extrait des features ML depuis une table SQL
    """

    connection = connections[db_alias]

    df = pd.read_sql(
        f'SELECT * FROM "{table_name}" LIMIT {limit}',
        connection
    )

    rows = []

    for col in df.columns:
        dtype = str(df[col].dtype)
        n_unique = df[col].nunique()

        avg_length = (
            df[col]
            .dropna()
            .astype(str)
            .map(len)
            .mean()
            if dtype.startswith("object") else 0
        )

        is_numeric = int(dtype in ("int64", "float64"))
        is_categ = int(dtype == "object" and n_unique <= 100)

        rows.append({
            "column_name": col,
            "dtype": dtype,
            "n_unique": n_unique,
            "avg_length": round(avg_length or 0, 1),
            "is_numeric": is_numeric,
            "is_categ": is_categ,
        })

    return pd.DataFrame(rows)
