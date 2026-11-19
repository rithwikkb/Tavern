from django.db import models
import uuid
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


# Inbox model is designed to have foreign key to an author, and generic foreign key to the object from the Inbox request (follow, post, like, comment)
#TODO: remove
class Inbox(models.Model):
    OBJECT_CHOICES = [
      ('follow', 'Follow request'),
      ('like', 'Like'),
      ('comment', 'Comment'),
      ('post', 'Post'),
    ]
          
    inbox_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    type = models.CharField(max_length=100, choices=OBJECT_CHOICES)
    author = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='author') #TODO: replace 'users.Author' with path to author
    created_at = models.DateTimeField("date requested", default=timezone.now)  # time zone aware

    # using generic foreign key so we can have "polymorphic" relationships between the tables (Like, Comment, Follow, Post)
    # https://docs.djangoproject.com/en/5.1/ref/contrib/contenttypes/#generic-relations for setting up generic foreign key 2024-10-14
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) 
    object_id = models.UUIDField(max_length=200) # TODO: changed it to UUID, fix errors..... for storing primary key value of the model itll be relating to 
    content_object = GenericForeignKey('content_type', 'object_id') # foreign key to Like or Comment, or Follow or Post

    def __str__(self):
      return f'{self.author} inbox'


