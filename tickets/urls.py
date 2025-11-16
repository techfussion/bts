from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # Auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Student Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('wallet/fund/', views.fund_wallet, name='fund_wallet'),
    path('booking/create/', views.create_booking, name='create_booking'),
    path('booking/history/', views.booking_history, name='booking_history'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    
    # Admin/Staff
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('scan-qr/', views.scan_qr, name='scan_qr'),
    path('verify-ticket/', views.verify_ticket, name='verify_ticket'),
]