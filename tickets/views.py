from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from .models import Wallet, WalletTransaction, Booking, Payment
import json
from .paystack_utils import PaystackAPI

# ============================================
# HOME & AUTHENTICATION VIEWS
# ============================================

def home(request):
    """Landing page"""
    return render(request, 'tickets/home.html')

def register(request):
    """Student registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('tickets:register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('tickets:register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('tickets:register')
        
        # Create user and wallet
        user = User.objects.create_user(username=username, email=email, password=password)
        Wallet.objects.create(user=user)
        
        messages.success(request, 'Registration successful! Please login.')
        return redirect('tickets:login')
    
    return render(request, 'tickets/register.html')

def user_login(request):
    """Student login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('tickets:dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'tickets/login.html')

@login_required
def user_logout(request):
    """Logout"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('tickets:home')


# ============================================
# STUDENT DASHBOARD & WALLET
# ============================================

@login_required
def dashboard(request):
    """Student dashboard"""
    wallet = request.user.wallet
    recent_bookings = request.user.bookings.all()[:5]
    recent_transactions = wallet.transactions.all()[:5]
    
    context = {
        'wallet': wallet,
        'recent_bookings': recent_bookings,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'tickets/dashboard.html', context)

@login_required
def fund_wallet(request):
    """Fund wallet - now supports both manual and Paystack"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero')
                return redirect('tickets:fund_wallet')
            
            wallet = request.user.wallet
            
            with transaction.atomic():
                wallet.balance += amount
                wallet.save()
                
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=amount,
                    description='Manual Wallet Funding'
                )
            
            messages.success(request, f'₦{amount} added to your wallet successfully!')
            return redirect('tickets:dashboard')
            
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount')
            return redirect('tickets:fund_wallet')
    
    # Pass Paystack public key to template
    from django.conf import settings
    context = {
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, 'tickets/fund_wallet.html', context)


# ============================================
# BOOKING SYSTEM
# ============================================

@login_required
def create_booking(request):
    """Create new booking"""
    wallet = request.user.wallet
    fare = Decimal('200.00')  # Fixed fare
    
    if request.method == 'POST':
        if wallet.balance < fare:
            messages.error(request, f'Insufficient balance. You need ₦{fare} but have ₦{wallet.balance}')
            return redirect('tickets:create_booking')
        
        with transaction.atomic():
            # Deduct from wallet
            wallet.balance -= fare
            wallet.save()
            
            # Create transaction record
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='DEBIT',
                amount=fare,
                description='Bus Ticket Purchase'
            )
            
            # Create booking
            booking = Booking.objects.create(
                user=request.user,
                fare=fare
            )
        
        messages.success(request, 'Ticket booked successfully!')
        return redirect('tickets:booking_detail', booking_id=booking.id)
    
    context = {
        'wallet': wallet,
        'fare': fare,
    }
    return render(request, 'tickets/create_booking.html', context)

@login_required
def booking_history(request):
    """View all bookings"""
    bookings = request.user.bookings.all()
    return render(request, 'tickets/booking_history.html', {'bookings': bookings})

@login_required
def booking_detail(request, booking_id):
    """View single booking with QR code"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'tickets/booking_detail.html', {'booking': booking})


# ============================================
# ADMIN/STAFF VIEWS
# ============================================

@login_required
def admin_dashboard(request):
    """Admin dashboard - view all bookings"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff only.')
        return redirect('tickets:dashboard')
    
    all_bookings = Booking.objects.all()
    active_bookings = all_bookings.filter(status='ACTIVE').count()
    used_bookings = all_bookings.filter(status='USED').count()
    
    context = {
        'all_bookings': all_bookings,
        'active_bookings': active_bookings,
        'used_bookings': used_bookings,
    }
    return render(request, 'tickets/admin_dashboard.html', context)

@login_required
def scan_qr(request):
    """QR Scanner page"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff only.')
        return redirect('tickets:dashboard')
    
    return render(request, 'tickets/scan_qr.html')

@login_required
def verify_ticket(request):
    """Verify and mark ticket as used"""
    if not request.user.is_staff:
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        data = json.loads(request.body)
        qr_data = data.get('qr_data', '')
        
        # Parse QR data: "BOOKING:XXX|TICKET:YYY|USER:ZZZ"
        try:
            parts = dict(item.split(':') for item in qr_data.split('|'))
            booking_ref = parts.get('BOOKING')
            
            booking = Booking.objects.get(booking_reference=booking_ref)
            
            if booking.status == 'USED':
                return JsonResponse({
                    'success': False,
                    'message': 'Ticket already used!',
                    'booking': None
                })
            
            # Mark as used
            booking.status = 'USED'
            booking.used_date = timezone.now()
            booking.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Ticket verified successfully!',
                'booking': {
                    'reference': booking.booking_reference,
                    'ticket_number': booking.ticket_number,
                    'user': booking.user.username,
                    'fare': str(booking.fare),
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M'),
                    'status': booking.status
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Invalid ticket: {str(e)}',
                'booking': None
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def initialize_payment(request):
    """Initialize Paystack payment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = Decimal(data.get('amount', 0))
            
            if amount < 100:
                return JsonResponse({'success': False, 'message': 'Minimum amount is ₦100'})
            
            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                amount=amount,
                email=request.user.email or f"{request.user.username}@buk.edu.ng"
            )
            
            # Initialize with Paystack
            paystack = PaystackAPI()
            response = paystack.initialize_transaction(
                email=payment.email,
                amount=amount,
                reference=payment.reference
            )
            
            if response.get('status'):
                return JsonResponse({
                    'success': True,
                    'authorization_url': response['data']['authorization_url'],
                    'reference': payment.reference
                })
            else:
                payment.status = 'FAILED'
                payment.save()
                return JsonResponse({'success': False, 'message': 'Payment failed'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def verify_payment(request, reference):
    """Verify payment and credit wallet"""
    try:
        payment = Payment.objects.get(reference=reference, user=request.user)
        
        if payment.status == 'SUCCESS':
            messages.info(request, 'Payment already processed')
            return redirect('tickets:dashboard')
        
        # Verify with Paystack
        paystack = PaystackAPI()
        response = paystack.verify_transaction(reference)
        
        if response.get('status') and response['data']['status'] == 'success':
            with transaction.atomic():
                payment.status = 'SUCCESS'
                payment.save()
                
                # Credit wallet
                wallet = request.user.wallet
                wallet.balance += payment.amount
                wallet.save()
                
                # Create transaction record
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=payment.amount,
                    description=f'Paystack Payment - Ref: {reference}'
                )
            
            messages.success(request, f'₦{payment.amount} added to your wallet!')
            return redirect('tickets:dashboard')
        else:
            payment.status = 'FAILED'
            payment.save()
            messages.error(request, 'Payment verification failed')
            return redirect('tickets:fund_wallet')
            
    except Payment.DoesNotExist:
        messages.error(request, 'Payment not found')
        return redirect('tickets:dashboard')