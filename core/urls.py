from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    signup_view, StudentLoginView, home_view, stall_detail_view,
    add_to_cart, view_cart, update_quantity, checkout_view,
    transaction_summary, download_receipt, mark_order_ready,
    test_logout_template, my_orders_view, order_history_view
)

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', StudentLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', home_view, name='home'),
    path('stall/<int:stall_id>/', stall_detail_view, name='stall_detail'),
    path('add-to-cart/<int:item_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', view_cart, name='view_cart'),
    path('update-quantity/<int:item_id>/', update_quantity, name='update_quantity'),
    path('checkout/<int:stall_id>/', checkout_view, name='checkout'),
    path('transaction/<str:transaction_id>/', transaction_summary, name='transaction_summary'),
    path('download-receipt/<str:transaction_id>/', download_receipt, name='download_receipt'),
    path('mark-ready/<str:transaction_id>/', mark_order_ready, name='mark_order_ready'),
    path('test-logout/', test_logout_template, name='test_logout'),
    path('my-orders/', my_orders_view, name='my_orders'),
    path('order-history/', order_history_view, name='order_history'),
]