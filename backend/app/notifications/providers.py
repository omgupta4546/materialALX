import abc
from app.notifications.schemas import NotificationResponse

# Abstract Base Provider
class BaseNotificationProvider(abc.ABC):
    @abc.abstractmethod
    def send(self, notification: NotificationResponse):
        pass

# In-Memory Store for Hackathon In-App Notifications
IN_MEMORY_NOTIFICATIONS = []

class InAppProvider(BaseNotificationProvider):
    def send(self, notification: NotificationResponse):
        # Simply append to our local state store
        IN_MEMORY_NOTIFICATIONS.append(notification)
        print(f"[InAppProvider] Stored notification {notification.id} for user {notification.user_id}")

class EmailProvider(BaseNotificationProvider):
    def send(self, notification: NotificationResponse):
        # Stub for future SendGrid/SMTP integration
        print(f"[EmailProvider] Would send email to user {notification.user_id} with title: {notification.title}")

class SMSProvider(BaseNotificationProvider):
    def send(self, notification: NotificationResponse):
        # Stub for future Twilio integration
        print(f"[SMSProvider] Would send SMS to user {notification.user_id}: {notification.title}")

# Configured active providers
ACTIVE_PROVIDERS = [
    InAppProvider(),
    EmailProvider(), # Active in logs only for demonstration
    SMSProvider()    # Active in logs only for demonstration
]
