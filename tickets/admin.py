from django.contrib import admin
from .models import Wallet, WalletTransaction, Booking

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'created_at']
    search_fields = ['user__username']

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'transaction_type', 'amount', 'timestamp']
    list_filter = ['transaction_type', 'timestamp']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'ticket_number', 'user', 'fare', 'status', 'booking_date']
    list_filter = ['status', 'booking_date']
    search_fields = ['booking_reference', 'ticket_number', 'user__username']