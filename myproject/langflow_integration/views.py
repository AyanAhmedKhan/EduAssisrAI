import requests
from django.http import JsonResponse
from django.conf import settings
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import *
from django.contrib.auth import authenticate,login,logout
from .helpers import send_forget_password_mail
import re
from django.contrib import messages
import uuid

LANGFLOW_API_URL = "https://api.langflow.astra.datastax.com"
LANGFLOW_ID = "d70d46de-ff2a-40f9-9ff9-924702813723"
FLOW_ID = "5bb89ea1-876d-4a89-a3df-65362c36f1cb"
APPLICATION_TOKEN = settings.LANGFLOW_APP_TOKEN  
# Load from settings

# Authentication Views

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Both username and password are required.')
            return redirect('login')
            
        user = authenticate(username=username, password=password)
        
        if user is None:
            messages.error(request, 'Invalid credentials.')
            return redirect('login')
            
        login(request, user)
        return redirect('home')
        
    return render(request, 'langflow_integration/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not all([username, email, password]):
            messages.error(request, 'All fields are required.')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user)
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('register')

    return render(request, 'langflow_integration/register.html')

def user_logout(request):
    logout(request)
    return redirect('landing')

@login_required
def home(request):
    return render(request, 'langflow_integration/home.html')

# Password Reset Views
@csrf_exempt

def forget_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        
        if not username:
            messages.error(request, 'Username is required.')
            return redirect('forget_password')
            
        try:
            user = User.objects.get(username=username)
            profile = Profile.objects.get(user=user)
            token = str(uuid.uuid4())
            profile.forget_password_token = token
            profile.save()
            
            send_forget_password_mail(user.email, token)
            messages.success(request, 'Password reset link sent to your email.')
            return redirect('forget_password')
            
        except User.DoesNotExist:
            messages.error(request, 'No user found with this username.')
            return redirect('forget_password')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('forget_password')
            
    return render(request, 'langflow_integration/forget-password.html')

def change_password(request, token):
    try:
        profile = Profile.objects.get(forget_password_token=token)
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not new_password or not confirm_password:
                messages.error(request, 'Both fields are required.')
                return redirect('change_password', token=token)
                
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('change_password', token=token)
                
            user = profile.user
            user.set_password(new_password)
            user.save()
            profile.forget_password_token = None
            profile.save()
            
            messages.success(request, 'Password changed successfully!')
            return redirect('login')
            
        return render(request, 'langflow_integration/change-password.html', {'token': token})
        
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid or expired token.')
        return redirect('forget_password')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('forget_password')

# Langflow API View (unchanged, but included for completeness)
from django.db import transaction
from django.db.utils import IntegrityError
@csrf_exempt
def langflow_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            if not user_message:
                return JsonResponse({"error": "The 'message' field is required."}, status=400)

            # Get or create chat session with proper handling
            try:
                if request.user.is_authenticated:
                    # Get or create session with transaction atomic to prevent race conditions
                    with transaction.atomic():
                        # Deactivate any other active sessions for this user
                        ChatSession.objects.filter(
                            user=request.user, 
                            is_active=True
                        ).update(is_active=False)
                        
                        # Create new active session
                        chat_session = ChatSession.objects.create(
                            user=request.user, 
                            is_active=True
                        )
                else:
                    session_key = request.session.session_key
                    if not session_key:
                        request.session.save()
                        session_key = request.session.session_key
                    
                    session = Session.objects.get(session_key=session_key)
                    
                    with transaction.atomic():
                        # Deactivate any other active sessions for this anonymous user
                        ChatSession.objects.filter(
                            session=session,
                            is_active=True
                        ).update(is_active=False)
                        
                        # Create new active session
                        chat_session = ChatSession.objects.create(
                            session=session,
                            is_active=True
                        )

            except IntegrityError as e:
                return JsonResponse({
                    "error": "Session creation failed due to database constraint. Please try again."
                }, status=500)
            except Exception as e:
                return JsonResponse({
                    "error": f"Session handling error: {str(e)}"
                }, status=500)
            
            # Save user message
            ChatMessage.objects.create(
                session=chat_session,
                message=user_message,
                is_bot=False
            )

            # Make the API request to Langflow
            payload = {
                "input_value": user_message,
                "output_type": "chat",
                "input_type": "chat",
            }
            headers = {
                "Authorization": f"Bearer {APPLICATION_TOKEN}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{LANGFLOW_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{FLOW_ID}",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            response_data = response.json()
            
            # Extract bot response
            bot_response = ""
            if 'outputs' in response_data:
                try:
                    bot_response = response_data['outputs'][0]['outputs'][0]['results']['message']['text']
                except (KeyError, IndexError):
                    try:
                        bot_response = response_data['outputs'][0]['outputs'][0]['outputs']['message']['message']
                    except (KeyError, IndexError):
                        try:
                            bot_response = response_data['outputs'][0]['outputs'][0]['messages'][0]['message']
                        except (KeyError, IndexError):
                            bot_response = str(response_data)  # fallback
            
            # Save bot response
            ChatMessage.objects.create(
                session=chat_session,
                message=bot_response,
                is_bot=True
            )

            return JsonResponse({"response": bot_response})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"Langflow API request failed: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
    
    
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Profile, ChatSession, ChatMessage
from django.contrib.sessions.models import Session


@login_required
def chat_history(request):
    try:
        chat_sessions = ChatSession.objects.filter(user=request.user)\
                          .prefetch_related('messages')\
                          .order_by('-updated_at')
        
        html = render_to_string(
            'langflow_integration/chat_history_items.html',
            {'chat_sessions': chat_sessions}
        )
        return JsonResponse({'html': html})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def load_chat(request, session_id):
    try:
        chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = chat_session.messages.all().values('message', 'is_bot', 'timestamp')
        
        return JsonResponse({
            'messages': [
                {
                    'text': msg['message'],
                    'is_bot': msg['is_bot'],
                    'timestamp': msg['timestamp'].strftime("%H:%M")
                } 
                for msg in messages
            ]
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Chat session not found'}, status=404)

@login_required
def new_chat(request):
    if request.method == 'POST':
        # Create a new chat session
        chat_session = ChatSession.objects.create(user=request.user)
        return JsonResponse({'session_id': chat_session.id})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def land(request):
    """Landing page view"""
    return render(request, 'langflow_integration/Land.html')


