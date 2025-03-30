
from django.db import models
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

class ChatSession(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        unique=False  # Remove unique=True if you have it
    )
    session = models.ForeignKey(
        Session, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        unique=False  # Remove unique=True if you have it
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_active_user_session',
                condition=models.Q(is_active=True)
            ),
            models.UniqueConstraint(
                fields=['session'],
                name='unique_active_anon_session',
                condition=models.Q(is_active=True)
            )
        ]

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    is_bot = models.BooleanField(default=False)  # False for user, True for bot
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        sender = "Bot" if self.is_bot else "User"
        return f"{sender}: {self.message[:50]}..."

class Profile(models.Model):
    user = models.OneToOneField(User , on_delete=models.CASCADE)
    forget_password_token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    