from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File
import uuid

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₦{self.balance}"

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} - ₦{self.amount}"

    class Meta:
        ordering = ['-timestamp']

class Booking(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('USED', 'Used'),
        ('EXPIRED', 'Expired'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    booking_reference = models.CharField(max_length=20, unique=True, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    fare = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    used_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.booking_reference} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"BUK{uuid.uuid4().hex[:8].upper()}"
        if not self.ticket_number:
            self.ticket_number = f"TKT{uuid.uuid4().hex[:10].upper()}"
        
        super().save(*args, **kwargs)
        
        # Generate QR code if not exists
        if not self.qr_code:
            qr_data = f"BOOKING:{self.booking_reference}|TICKET:{self.ticket_number}|USER:{self.user.username}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            file_name = f'qr_{self.booking_reference}.png'
            self.qr_code.save(file_name, File(buffer), save=False)
            buffer.close()
            super().save(update_fields=['qr_code'])

    class Meta:
        ordering = ['-booking_date']