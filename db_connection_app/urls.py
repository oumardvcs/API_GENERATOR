from django.urls import path
from .views import connect_database,show_tables,export_table,train_model

urlpatterns = [
    path("", connect_database, name="connect_db"),
    path('tables/', show_tables, name='show_tables'),
     path("tables/<str:table_name>/", show_tables, name="show_table"),
         path('export/<str:table_name>/<str:format>/', export_table, name='export_table'),
         path('train', train_model, name='train_model'),

    
]