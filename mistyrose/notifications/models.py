import uuid
from django.db import models


class Notification(models.Model):
    """
    Tells an author that someone liked or commented on their content, or followed them.

    Each notification points at the like, comment or follow that caused it, so undoing
    that action (unliking, deleting the comment, declining the request) deletes the
    notification too.
    """
    LIKE_POST = 'like_post'
    LIKE_COMMENT = 'like_comment'
    COMMENT = 'comment'
    FOLLOW_REQUEST = 'follow_request'
    FOLLOW = 'follow'
    FOLLOW_ACCEPTED = 'follow_accepted'
    VERB_CHOICES = [
        (LIKE_POST, 'liked your post'),
        (LIKE_COMMENT, 'liked your comment'),
        (COMMENT, 'commented on your post'),
        (FOLLOW_REQUEST, 'wants to follow you'),
        (FOLLOW, 'started following you'),
        (FOLLOW_ACCEPTED, 'accepted your follow request'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='+')
    verb = models.CharField(max_length=20, choices=VERB_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    # what caused it and the post (or comment) it's about, if any
    like = models.ForeignKey('posts.Like', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    comment = models.ForeignKey('posts.Comment', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    follow = models.ForeignKey('users.Follows', on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['-created']
        indexes = [models.Index(fields=['recipient', 'read'])]

    def __str__(self):
        return f'{self.actor} {self.get_verb_display()} ({self.recipient})'
