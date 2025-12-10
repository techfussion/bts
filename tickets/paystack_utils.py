import requests
from django.conf import settings

class PaystackAPI:
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(self, email, amount, reference):
        """Initialize payment - amount in naira"""
        url = f"{self.BASE_URL}/transaction/initialize"
        data = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "reference": reference,
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
    
    def verify_transaction(self, reference):
        """Verify payment"""
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        response = requests.get(url, headers=self.headers)
        return response.json()