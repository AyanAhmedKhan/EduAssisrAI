from django.db import migrations

def clean_duplicate_sessions(apps, schema_editor):
    ChatSession = apps.get_model('langflow_integration', 'ChatSession')
    
    # For authenticated users
    User = apps.get_model('auth', 'User')
    for user in User.objects.all():
        sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')
        if sessions.count() > 1:
            # Keep the most recent session
            for session in sessions[1:]:
                session.delete()
    
    # For anonymous sessions
    Session = apps.get_model('sessions', 'Session')
    for session in Session.objects.all():
        chat_sessions = ChatSession.objects.filter(session=session).order_by('-updated_at')
        if chat_sessions.count() > 1:
            # Keep the most recent session
            for chat_session in chat_sessions[1:]:
                chat_session.delete()

class Migration(migrations.Migration):
    dependencies = [
        ('langflow_integration', '0001_initial'),  # Use your actual last migration
        ('sessions', '0001_initial'),  # Required for Session model
    ]

    operations = [
        migrations.RunPython(clean_duplicate_sessions),
    ]