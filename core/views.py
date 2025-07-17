from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.timezone import now, make_aware, localtime, localdate
from django.utils.crypto import get_random_string

from .forms import SignUpForm, CheckoutForm
from .models import CustomUser, Stall, Order, MenuItem, CartItem, OrderItem, Voucher

from reportlab.pdfgen import canvas
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time
import pytz
import requests
import io
import json
import hmac
import hashlib

class StudentLoginView(LoginView):
    template_name = 'core/login.html'

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def home_view(request):
    user = request.user
    if user.blacklisted:
        unpaid_orders = Order.objects.filter(user=user, is_paid=False)
        return render(request, 'core/blacklisted.html', {'orders': unpaid_orders})
    stalls = Stall.objects.all()
    pending_orders = Order.objects.filter(user=user, is_complete=False).order_by('-created_at')
    order_history = Order.objects.filter(user=user).order_by('-created_at')
    return render(request, 'core/home.html', {
        'user': user,
        'stalls': stalls,
        'orders': order_history,
        'pending_orders': pending_orders,
    })

@login_required
def stall_detail_view(request, stall_id):
    stall = Stall.objects.get(id=stall_id)
    food_items = MenuItem.objects.filter(stall=stall, category='Food')
    beverage_items = MenuItem.objects.filter(stall=stall, category='Beverage')
    return render(request, 'core/stall_detail.html', {
        'stall': stall,
        'food_items': food_items,
        'beverage_items': beverage_items,
    })

@login_required
def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        item=item,
        stall=item.stall,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{item.name} added to cart!")
    return redirect('stall_detail', stall_id=item.stall.id)

@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('stall', 'item')
    grouped_cart = defaultdict(list)
    total_per_stall = {}
    for item in cart_items:
        grouped_cart[item.stall].append(item)
        total_per_stall[item.stall] = total_per_stall.get(item.stall, 0) + item.subtotal()
    return render(request, 'core/cart.html', {
        'grouped_cart': dict(grouped_cart),
        'total_per_stall': total_per_stall
    })

@require_POST
@login_required
def update_quantity(request, item_id):
    action = request.POST.get("action")
    cart_item = CartItem.objects.get(id=item_id, user=request.user)
    if action == "increase":
        cart_item.quantity += 1
    elif action == "decrease" and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif action == "remove":
        cart_item.delete()
        return redirect('view_cart')
    cart_item.save()
    return redirect('view_cart')

@login_required
def transaction_summary(request, transaction_id):
    try:
        order = Order.objects.get(transaction_id=transaction_id, user=request.user)
        order_items = OrderItem.objects.filter(order=order)
    except Order.DoesNotExist:
        raise Http404("Transaction not found.")
    pending_count = Order.objects.filter(stall=order.stall, status='Pending').count()
    estimated_minutes = 10 * pending_count
    return render(request, 'core/transaction_summary.html', {
        'order': order,
        'order_items': order_items,
        'estimated_minutes': estimated_minutes,
    })

@login_required
def download_receipt(request, transaction_id):
    try:
        order = Order.objects.get(transaction_id=transaction_id, user=request.user)
        order_items = OrderItem.objects.filter(order=order)
    except Order.DoesNotExist:
        raise Http404("Transaction not found.")
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 12)
    y = 800
    p.drawString(100, y, f"Transaction ID: {order.transaction_id}")
    y -= 20
    p.drawString(100, y, f"Stall: {order.stall.name}")
    y -= 20
    p.drawString(100, y, f"Pickup Time: {order.pickup_time.strftime('%Y-%m-%d %H:%M')}")
    y -= 20
    if order.voucher:
        p.drawString(100, y, f"Voucher: {order.voucher.code} - ₱{order.voucher.discount_amount} off")
        y -= 20
    p.drawString(100, y, f"Total Cost: ₱{order.total_cost}")
    y -= 40
    for item in order_items:
        p.drawString(100, y, f"{item.item.name} × {item.quantity} = ₱{item.item.price * item.quantity}")
        y -= 20
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order.transaction_id}.pdf"'
    return response

@login_required
def checkout_view(request, stall_id):
    stall = Stall.objects.get(id=stall_id)
    cart_items = CartItem.objects.filter(user=request.user, stall=stall)
    if not cart_items:
        return redirect('view_cart')

    discount = 0
    voucher_code = request.GET.get('voucher', '')
    voucher = None
    if voucher_code:
        try:
            voucher = Voucher.objects.get(code=voucher_code, stall=stall, is_active=True)
            discount = voucher.discount_amount
        except Voucher.DoesNotExist:
            messages.warning(request, "Invalid or inactive voucher code.")

    total = sum(item.subtotal() for item in cart_items) - discount
    total = max(total, 0)

    manila_tz = pytz.timezone("Asia/Manila")
    current_time = now().astimezone(manila_tz)
    opening_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    right_now_dt = opening_time + timedelta(minutes=15) if current_time < opening_time else current_time + timedelta(minutes=stall.average_lead_time)

    pickup_options = []
    if current_time >= opening_time:
        label = f"Right Now (pick-up at {right_now_dt.strftime('%H:%M')})"
        pickup_options.append((label, label))

    minute = right_now_dt.minute
    next_10 = ((minute // 10) + 1) * 10
    if next_10 == 60:
        right_now_dt += timedelta(hours=1)
        next_10 = 0
    rounded_start = right_now_dt.replace(minute=next_10, second=0, microsecond=0)

    closing_time = stall.closing_time or dt_time(17, 0)
    closing_dt = make_aware(datetime.combine(current_time.date(), closing_time))

    while rounded_start < closing_dt:
        label = rounded_start.strftime("%H:%M")
        pickup_options.append((label, label))
        rounded_start += timedelta(minutes=10)

    if request.method == 'POST':
        form = CheckoutForm(request.POST, pickup_options=pickup_options)
        if form.is_valid():
            pickup_time_str = form.cleaned_data['pickup_time']
            if pickup_time_str.startswith("Right Now"):
                pickup_dt = now() + timedelta(minutes=stall.average_lead_time)
            else:
                today = now().date()
                pickup_dt = datetime.combine(today, datetime.strptime(pickup_time_str, "%H:%M").time())
            today = localdate()
            existing_orders = Order.objects.filter(stall=stall, created_at__date=today)
            stall_index = list(Stall.objects.order_by('id').values_list('id', flat=True)).index(stall.id) + 1
            transaction_number = existing_orders.count() + 1
            transaction_id = f"S{stall_index:02d}{transaction_number:03d}"

            headers = {
                "Authorization": f"Basic {settings.PAYMONGO_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "data": {
                    "attributes": {
                        "line_items": [{
                            "currency": "PHP",
                            "amount": int(total * 100),
                            "description": f"Order from {stall.name}",
                            "name": transaction_id,
                            "quantity": 1
                        }],
                        "payment_method_types": ["gcash", "paymaya", "card"],
                        "success_url": f"http://localhost:8000/transaction/{transaction_id}/",
                        "cancel_url": "http://localhost:8000/cart/"
                    }
                }
            }

            response = requests.post("https://api.paymongo.com/v1/checkout_sessions", json=data, headers=headers)
            if response.status_code not in [200, 201]:
                messages.error(request, "Failed to create payment session. Please try again later.")
                return redirect('view_cart')

            checkout_url = response.json()["data"]["attributes"]["checkout_url"]

            order = Order.objects.create(
                user=request.user,
                stall=stall,
                pickup_time=pickup_dt,
                total_cost=total,
                transaction_id=transaction_id,
                status="Pending",
                voucher=voucher
            )

            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    item=cart_item.item,
                    quantity=cart_item.quantity
                )

            cart_items.delete()
            return redirect(checkout_url)
    else:
        form = CheckoutForm(pickup_options=pickup_options)

    return render(request, 'core/checkout.html', {
        'stall': stall,
        'cart_items': cart_items,
        'form': form,
        'total': total,
        'voucher_code': voucher_code,
        'discount': discount,
    })

@login_required
def mark_order_ready(request, transaction_id):
    order = Order.objects.get(transaction_id=transaction_id)
    if not request.user.is_staff or order.stall.name[:3].lower() not in request.user.student_id.lower():
        return HttpResponse("Unauthorized", status=403)
    order.status = "Ready"
    order.save()
    messages.success(request, "Order marked as ready!")
    if order.user.email:
        send_mail(
            subject="Your order is ready!",
            message=f"Hi {order.user.full_name},\n\nYour order {order.transaction_id} from {order.stall.name} is ready for pickup!",
            from_email="noreply@digitalcafe.com",
            recipient_list=[order.user.email],
        )
    print(f"[SMS] Order {order.transaction_id} ready for pickup! Sent to {order.user.contact_number}")
    return redirect('transaction_summary', transaction_id=transaction_id)

def custom_logout_view(request):
    logout(request)
    return render(request, 'core/logout.html')

def test_logout_template(request):
    return render(request, 'core/logout.html')

def auto_blacklist_users():
    unpaid_orders = Order.objects.filter(is_paid=False, status="Pending")
    for order in unpaid_orders:
        user = order.user
        user.blacklisted = True
        user.save()

@login_required
def my_orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/my_orders.html', {'orders': orders})

@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/order_history.html', {'orders': orders})

@csrf_exempt
def paymongo_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = request.body
    sig_header = request.headers.get('Paymongo-Signature', '')
    secret_key = 'your_paymongo_webhook_secret'
    computed_signature = hmac.new(
        key=bytes(secret_key, 'utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, sig_header):
        return HttpResponse("Invalid signature", status=403)

    data = json.loads(payload)
    event_type = data["data"]["attributes"]["type"]

    if event_type == "payment.paid":
        reference = data["data"]["attributes"]["data"]["attributes"]["description"]
        try:
            order = Order.objects.get(transaction_id=reference)
            order.is_paid = True
            order.save()
        except Order.DoesNotExist:
            return HttpResponse("Order not found", status=404)

    return JsonResponse({"status": "received"})

def handle_paymongo_webhook(payload):
    transaction_id = payload["data"]["attributes"]["reference_number"]
    payment_status = payload["data"]["attributes"]["status"]
    if payment_status == "paid":
        try:
            order = Order.objects.get(transaction_id=transaction_id)
            order.is_paid = True
            order.save()
        except Order.DoesNotExist:
            pass
