from django.db.models.signals import post_save
from django.dispatch import receiver

from posts.models import Comment, Like, Post
from users.models import Follows
from .models import Notification


def notify(recipient, actor, verb, **source):
    # nobody gets notified about their own actions
    if recipient is None or actor is None or recipient.id == actor.id:
        return
    Notification.objects.get_or_create(recipient=recipient, actor=actor, verb=verb, **source)


@receiver(post_save, sender=Like)
def like_saved(sender, instance, created, **kwargs):
    if not created:
        return
    target = instance.content_object
    if isinstance(target, Post):
        notify(target.author_id, instance.author_id, Notification.LIKE_POST, like=instance, post=target)
    elif isinstance(target, Comment):
        notify(target.author_id, instance.author_id, Notification.LIKE_COMMENT,
               like=instance, comment=target, post=target.post_id)


@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    if created:
        notify(instance.post_id.author_id, instance.author_id, Notification.COMMENT,
               comment=instance, post=instance.post_id)


@receiver(post_save, sender=Follows)
def follow_saved(sender, instance, **kwargs):
    """
    Keep a follow's notifications in step with its status: a pending request shows as
    "wants to follow you"; once accepted it becomes "started following you" and the
    follower hears that their request was accepted.
    """
    follower, followed = instance.local_follower_id, instance.followed_id
    if follower is None:
        return
    to_followed = Notification.objects.filter(follow=instance, recipient=followed)
    if instance.status == 'PENDING':
        Notification.objects.filter(follow=instance, verb=Notification.FOLLOW_ACCEPTED).delete()
        if to_followed.exists():
            to_followed.update(verb=Notification.FOLLOW_REQUEST, read=False)
        else:
            notify(followed, follower, Notification.FOLLOW_REQUEST, follow=instance)
    elif instance.status == 'ACCEPTED':
        was_requested = to_followed.filter(verb=Notification.FOLLOW_REQUEST).exists()
        if to_followed.exists():
            # accepting means you've seen the request, so it isn't unread any more
            to_followed.update(verb=Notification.FOLLOW, read=True)
        else:
            notify(followed, follower, Notification.FOLLOW, follow=instance)
        if was_requested:
            notify(follower, followed, Notification.FOLLOW_ACCEPTED, follow=instance)


def rebuild_notifications_for(author):
    """
    Recreate any missing notifications about activity on `author`'s posts, comments and
    follows (used when the demo account resets, since visitors can dismiss them and
    old ones expire).
    """
    post_ids = list(Post.objects.filter(author_id=author).values_list('id', flat=True))
    comment_ids = list(Comment.objects.filter(author_id=author).values_list('id', flat=True))
    for like in Like.objects.filter(object_id__in=post_ids + comment_ids):
        like_saved(Like, like, created=True)
    for comment in Comment.objects.filter(post_id__in=post_ids).select_related('post_id__author_id', 'author_id'):
        comment_saved(Comment, comment, created=True)
    for follow in Follows.objects.filter(followed_id=author):
        follow_saved(Follows, follow)
