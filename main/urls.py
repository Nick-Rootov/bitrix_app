from django.contrib import admin
from django.urls import path
from main import views

app_name = 'main'

urlpatterns = [
    path('', views.start, name='start'),
    path('home/', views.index, name='index'),
    path('last-active-deals/', views.last_active_deals, name='last_active_deals'),
    path('add-deal/', views.add_deal, name='add_deal'),
    path('qr-generate/', views.qr_generate, name='qr_generate'),
    path('product/<signed_id>/', views.product_detail, name='product_detail'),
    path('users_list/', views.active_users_list, name='active_users_list'),
    path('calls-generate/', views.calls_generate, name='calls_generate'),
]
