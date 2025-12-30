from django.shortcuts import render,redirect
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError

ENGINE_MAP = {
    "postgresql": "django.db.backends.postgresql",
    "mysql": "django.db.backends.mysql",
    "sqlite": "django.db.backends.sqlite3",
}

def connect_database(request):
    if request.method == "POST":
        db_type = request.POST.get("type")
        host = request.POST.get("host")
        port = request.POST.get("port")
        name = request.POST.get("db_name")
        user = request.POST.get("user")
        password = request.POST.get("password")

        if db_type not in ENGINE_MAP:
            return render(request, "db_connection_app/connector.html", {"error": "Unsupported database type"})

        db_alias = "dynamic_db"

        settings.DATABASES[db_alias] = {
            "ENGINE": ENGINE_MAP[db_type],
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
            "ATOMIC_REQUESTS": True,
            "CONN_MAX_AGE": 0,
              "CONN_HEALTH_CHECKS": True,
              "AUTOCOMMIT": True,
            "OPTIONS": {"sslmode": "require"} if db_type == "postgresql" else {},
             "TIME_ZONE": "UTC", 
        }

        try:
            connection = connections[db_alias]
            connection.ensure_connection()
            request.session['db_alias'] = db_alias

            return redirect('show_tables')
        except OperationalError as e:
            return render(request, "db_connection_app/connector.html", {"error": str(e)})

    # GET → simple affichage du formulaire
    return render(request, "db_connection_app/connector.html")


from django.shortcuts import render, redirect
from django.db import connections, OperationalError

NUMERIC_TYPES = (
    "int", "integer", "bigint", "smallint",
    "numeric", "decimal", "real", "double",
    "float"
)

def show_tables(request, table_name=None):
    db_alias = request.session.get('db_alias')

    if not db_alias or db_alias not in connections.databases:
        return redirect('connect_db')

    connection = connections[db_alias]
    db_info = connection.settings_dict

    # ========================
    # Récupérer les tables
    # ========================
    tables = []
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
        elif connection.vendor == "mysql":
            cursor.execute("SHOW TABLES;")
        else:
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%';
            """)
        tables = [row[0] for row in cursor.fetchall()]

    # ========================
    # Paramètres GET
    # ========================
    try:
        limit = int(request.GET.get("limit", 50))
        if limit <= 0:
            limit = 50
    except ValueError:
        limit = 50

    selected_columns = request.GET.getlist("cols")

    columns = []
    data = []
    column_types = {}
    numeric_columns = []
    categorical_columns = []
    category_values = {}

    # ========================
    # Si table sélectionnée
    # ========================
    if table_name:
        with connection.cursor() as cursor:

            # -------- Colonnes + types --------
            if connection.vendor == "postgresql":
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s;
                """, [table_name])
                column_types = dict(cursor.fetchall())

            elif connection.vendor == "mysql":
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND table_schema = DATABASE();
                """, [table_name])
                column_types = dict(cursor.fetchall())

            else:  # sqlite
                cursor.execute(f"PRAGMA table_info({table_name});")
                for col in cursor.fetchall():
                    column_types[col[1]] = col[2]

            columns = list(column_types.keys())

            numeric_columns = [
                c for c, t in column_types.items()
                if any(x in t.lower() for x in NUMERIC_TYPES)
            ]

            categorical_columns = [
                c for c in columns if c not in numeric_columns
            ]

            if not selected_columns:
                selected_columns = columns

            # -------- Récupérer catégories --------
            for col in categorical_columns:
                try:
                    cursor.execute(
                        f'SELECT DISTINCT "{col}" FROM "{table_name}" LIMIT 100;'
                        if connection.vendor == "postgresql"
                        else f"SELECT DISTINCT `{col}` FROM `{table_name}` LIMIT 100;"
                    )
                    category_values[col] = [r[0] for r in cursor.fetchall() if r[0] is not None]
                except:
                    category_values[col] = []

            # -------- Construire filtres --------
            filters = []
            params = []

            # Numériques
            for col in numeric_columns:
                min_val = request.GET.get(f"{col}_min")
                max_val = request.GET.get(f"{col}_max")

                if min_val:
                    filters.append(f'"{col}" >= %s')
                    params.append(min_val)
                if max_val:
                    filters.append(f'"{col}" <= %s')
                    params.append(max_val)

            # Catégories
            for col in categorical_columns:
                val = request.GET.get(col)
                if val:
                    filters.append(f'"{col}" = %s')
                    params.append(val)

            where_sql = ""
            if filters:
                where_sql = "WHERE " + " AND ".join(filters)

            # -------- Colonnes SQL --------
            cols_sql = ", ".join([f'"{c}"' for c in selected_columns])

            query = f"""
                SELECT {cols_sql}
                FROM "{table_name}"
                {where_sql}
                LIMIT {limit};
            """

            cursor.execute(query, params)
            data = cursor.fetchall()

    return render(request, "db_connection_app/show_tables.html", {
        "tables": tables,
        "selected_table": table_name,
        "columns": columns,
        "selected_columns": selected_columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "category_values": category_values,
        "data": data,
        "limit": limit,
        "db_info": db_info,
    })


from django.http import HttpResponse, JsonResponse
from django.db import connections

NUMERIC_TYPES = (
    "int", "integer", "bigint", "smallint",
    "numeric", "decimal", "real", "double",
    "float"
)

def export_table(request, table_name, format):
    db_alias = request.session.get('db_alias')
    if not db_alias or db_alias not in connections.databases:
        return HttpResponse("Pas de connexion à la base.", status=400)

    connection = connections[db_alias]

    try:
        with connection.cursor() as cursor:
            # -------- Colonnes + types --------
            if connection.vendor == "postgresql":
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s;
                """, [table_name])
                column_types = dict(cursor.fetchall())
            elif connection.vendor == "mysql":
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND table_schema = DATABASE();
                """, [table_name])
                column_types = dict(cursor.fetchall())
            else:
                cursor.execute(f"PRAGMA table_info({table_name});")
                column_types = {col[1]: col[2] for col in cursor.fetchall()}

            columns = list(column_types.keys())
            numeric_columns = [c for c, t in column_types.items() if any(x in t.lower() for x in NUMERIC_TYPES)]
            categorical_columns = [c for c in columns if c not in numeric_columns]

            # -------- Construire filtres --------
            filters = []
            params = []

            # Numériques
            for col in numeric_columns:
                min_val = request.GET.get(f"{col}_min")
                max_val = request.GET.get(f"{col}_max")
                if min_val:
                    filters.append(f'"{col}" >= %s')
                    params.append(min_val)
                if max_val:
                    filters.append(f'"{col}" <= %s')
                    params.append(max_val)

            # Catégories
            for col in categorical_columns:
                val = request.GET.get(col)
                if val:
                    filters.append(f'"{col}" = %s')
                    params.append(val)

            where_sql = ""
            if filters:
                where_sql = "WHERE " + " AND ".join(filters)

            # -------- Colonnes SQL --------
            cols_sql = ", ".join([f'"{c}"' for c in columns])

            query = f'SELECT {cols_sql} FROM "{table_name}" {where_sql};'
            cursor.execute(query, params)
            rows = cursor.fetchall()

            column_names = [col[0] for col in cursor.description]

    except Exception as e:
        return HttpResponse(f"Erreur : {str(e)}", status=400)

    # -------- Export --------
    if format == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{table_name}.csv"'
        writer = csv.writer(response)
        writer.writerow(column_names)
        writer.writerows(rows)
        return response

    elif format == 'json':
        data = [dict(zip(column_names, row)) for row in rows]
        return JsonResponse(data, safe=False)

    else:
        return HttpResponse("Format non supporté", status=400)


from ia.ml.train_from_db import collect_training_data

def train_model(request):
    db_alias = request.session.get('db_alias')
    if not db_alias:
        return render(request, "db_connection_app/connector.html", {"error": "Connectez d'abord la DB."})

    try:
        collect_training_data(db_alias)
        return render(request, "db_connection_app/success.html", {"message": "Modèle entraîné !"})
    except Exception as e:
        return render(request, "db_connection_app/connector.html", {"error": str(e)})
