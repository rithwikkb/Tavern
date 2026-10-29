import uuid
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.views import can_view_post
from users.utils import get_request_author
from .models import Notification

# the list shows at most this many of the newest notifications
NOTIFICATION_LIMIT = 50
# like most social apps, notifications expire after a while
NOTIFICATION_MAX_AGE = timedelta(days=30)


def author_summary(author):
    return {
        'id': str(author.id),
        'displayName': author.display_name,
        'profileImage': author.profile_image or '',
    }


def visible_notifications(author):
    """
    The author's notifications from the last 30 days (older ones are deleted on the way),
    skipping ones about posts that have since been deleted.
    """
    cutoff = timezone.now() - NOTIFICATION_MAX_AGE
    Notification.objects.filter(recipient=author, created__lt=cutoff).delete()
    return Notification.objects.filter(recipient=author).exclude(
        Q(post__isnull=False) & Q(post__visibility='DELETED')
    )


class NotificationsView(APIView):
    """
    GET: the logged-in author's newest notifications and how many are unread.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        author = get_request_author(request)
        if author is None:
            return Response(status=status.HTTP_403_FORBIDDEN)

        notifications = visible_notifications(author).select_related(
            'actor', 'post', 'post__author_id', 'comment', 'like'
        )[:NOTIFICATION_LIMIT]

        items = []
        for n in notifications:
            post = n.post
            # e.g. a friends-only post the recipient commented on before an unfriending
            if post is not None and not can_view_post(request, post):
                continue
            # show when the like or comment happened (seeded demo data is backdated)
            when = (n.comment.published if n.verb == Notification.COMMENT and n.comment
                    else n.like.published if n.like and n.like.published
                    else n.created)
            items.append({
                'id': str(n.id),
                'verb': n.verb,
                'text': n.get_verb_display(),
                'read': n.read,
                'created': when,
                'actor': author_summary(n.actor),
                'post': {'id': str(post.id), 'title': post.title or ''} if post else None,
                # the comment's text for comments, or the liked comment's text
                'comment': n.comment.comment if n.comment else None,
                'commentId': str(n.comment_id) if n.comment_id else None,
            })

        items.sort(key=lambda item: item['created'], reverse=True)
        return Response({
            'unread_count': visible_notifications(author).filter(read=False).count(),
            'notifications': items,
        })


class UnreadCountView(APIView):
    """
    GET: just the unread count, for the badge in the navigation bar.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        author = get_request_author(request)
        if author is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response({'unread_count': visible_notifications(author).filter(read=False).count()})


class MarkReadView(APIView):
    """
    POST: mark all of the logged-in author's notifications as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        author = get_request_author(request)
        if author is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        Notification.objects.filter(recipient=author, read=False).update(read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DismissView(APIView):
    """
    POST {"ids": [...]}: remove some of the logged-in author's notifications from their list.
    (The like, comment or follow itself stays.)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        author = get_request_author(request)
        if author is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        ids = request.data.get('ids')
        if not isinstance(ids, list) or not ids or len(ids) > NOTIFICATION_LIMIT:
            return Response({'error': 'ids must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)
        valid_ids = []
        for value in ids:
            try:
                valid_ids.append(uuid.UUID(str(value)))
            except ValueError:
                return Response({'error': 'Invalid notification id.'}, status=status.HTTP_400_BAD_REQUEST)
        # only ever the requester's own notifications
        Notification.objects.filter(recipient=author, id__in=valid_ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
