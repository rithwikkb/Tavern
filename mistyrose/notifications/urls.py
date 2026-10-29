from django.urls import path
from .views import DismissView, MarkReadView, NotificationsView, UnreadCountView

urlpatterns = [
    path('', NotificationsView.as_view(), name='notifications'),
    path('unread_count/', UnreadCountView.as_view(), name='notifications-unread-count'),
    path('read/', MarkReadView.as_view(), name='notifications-read'),
    path('dismiss/', DismissView.as_view(), name='notifications-dismiss'),
]
