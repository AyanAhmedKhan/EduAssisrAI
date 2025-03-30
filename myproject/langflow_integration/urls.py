from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Map the home view to /langflow/
    path('query/', views.langflow_query, name='langflow_query'),  # Map the query view to /langflow/query/
    path('Land/', views.land, name='Land'),  # Map the land view to /langflow/land/
    path("accounts/",include("django.contrib.auth.urls")),
    path('login/' , views.user_login , name="login"),
    path('register/' , views.register , name="register"),
    path('forget-password/' , views.forget_password , name="forget_password"),
    path('change-password/<token>/' , views.change_password , name="change_password"),
    path('logout/' , views.logout , name="logout"),
    path('chat-history/', views.chat_history, name="chat_history"),
    path('load-chat/<int:session_id>/', views.load_chat, name="load_chat"),
    path('new-chat/', views.new_chat, name="new_chat"),
]