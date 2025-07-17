from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, student_id, full_name, contact_number, email, password=None):
        if not student_id:
            raise ValueError("Student ID is required")
        user = self.model(
            student_id=student_id,
            full_name=full_name,
            contact_number=contact_number,
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, full_name, contact_number, email, password):
        user = self.create_user(student_id, full_name, contact_number, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    student_id = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    blacklisted = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['full_name', 'contact_number', 'email']

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

class Stall(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stalls', null=True, blank=True)
    logo_filename = models.CharField(max_length=100, blank=True, null=True)
    average_lead_time = models.IntegerField(default=15)
    closing_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    CATEGORY_CHOICES = (
        ('Food', 'Food'),
        ('Beverage', 'Beverage'),
    )

    stall = models.ForeignKey(Stall, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.stall.name})"

class CartItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.item.price * self.quantity

    def __str__(self):
        return f"{self.item.name} × {self.quantity} - {self.user.full_name}"

ORDER_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Ready", "Ready"),
    ("Cancelled", "Cancelled")
]

def default_pickup_time():
    return timezone.now() + timedelta(minutes=30)

def get_default_stall():
    return 17

def get_default_user():
    return 4

def default_transaction_id():
    return f"TEMP{int(timezone.now().timestamp())}"

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=get_default_user)
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, default=get_default_stall)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='Pending')
    pickup_time = models.DateTimeField(default=default_pickup_time)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_id = models.CharField(max_length=50, default=default_transaction_id)
    is_paid = models.BooleanField(default=False)
    voucher = models.ForeignKey('Voucher', on_delete=models.SET_NULL, null=True, blank=True, default=None)
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.transaction_id} - {self.user.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    voucher = models.ForeignKey('Voucher', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.item.name} × {self.quantity} ({self.order.transaction_id})"

class Voucher(models.Model):
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, related_name='vouchers')
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - ₱{self.discount_amount} ({'Active' if self.is_active else 'Inactive'})"
