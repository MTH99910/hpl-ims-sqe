"""
Inventory App - URL Configuration
"""

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Item URLs
    path('', views.ItemListView.as_view(), name='list'),
    path('create/', views.ItemCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ItemDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.ItemUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.item_delete_view, name='delete'),
    path('<int:pk>/adjust/', views.StockAdjustmentView.as_view(), name='adjust'),
    
    # Location URLs
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/create/', views.LocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/update/', views.LocationUpdateView.as_view(), name='location_update'),
    
    # Transaction URLs
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    
    # API endpoints
    path('api/item-details/', views.get_item_details, name='item_details_api'),
]
