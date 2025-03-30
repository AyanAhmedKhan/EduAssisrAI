from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('langflow/', include('langflow_integration.urls')),  # Include app URLs
    #path('' , include('accounts.urls')),
]

