from django.contrib import admin
from core.admin import admin_site
from django.urls import path, include
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('admin/login/', admin_site.login, name='admin_login'), 
    path('admin/logout/', LogoutView.as_view(next_page='/admin/login/'), name='admin_logout'),
    path('admin/', admin_site.urls),
    path('', include('core.urls')),
]