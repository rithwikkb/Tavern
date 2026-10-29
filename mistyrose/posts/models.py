import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError # Remove this!

# Create your models here.
class Post(models.Model):
    TYPE_CHOICES = [('post', 'Post')]
    
    VISIBILITY_CHOICES = [
      ('FRIENDS', 'Friends'),
      ('PUBLIC', 'Public'),
      ('UNLISTED', 'Unlisted'),
      ('DELETED', 'Deleted'),
      ('SHARED', 'Shared')
    ]
    
    CONTENT_TYPE_CHOICES = [
      ('text/plain', 'Plain'),
      ('text/markdown', 'Markdown'),
      ('image/png;base64', 'PNG Image'),
      ('image/jpeg;base64', 'JPEG Image'),
      ('image/gif;base64', 'GIF Image'),  # teehee this one is a bonus
    ]
    
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='post')
    title = models.CharField(max_length=200, blank=True, null=True, default='No Title')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True, editable=False, blank=True, null=True) #identify post by url
    author_id = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='posts')
    description = models.TextField(blank=True, null=True, editable=True, default='No Description')
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES, default='text/plain')
    content = models.TextField(blank=True, null=True)
    published = models.DateTimeField(auto_now=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='PUBLIC')
    original_url = models.JSONField(blank=True, null=True)

    # generic relation for reverse lookup for 'Like' objects on the post - because we are using generic foreign key in the like
    likes = GenericRelation('Like')

    def save(self, *args, **kwargs):
        # create url using the author's url and post id 
        if not self.url:
            self.url = f"{self.author_id.url.rstrip('/')}/posts/{self.id}/"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    # Remove this
    def clean(self):
        # Custom validation to ensure original_url is set for shared posts
        if self.visibility == 'SHARED' and not self.original_url:
            raise ValidationError("Original URL must be provided for shared posts.")
        super().clean()
      
    class Meta:
        ordering = ['-published']
      
class Like(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True, editable=False, blank=True, null=True) #identify like by url
    author_id = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='likes') 
    published = models.DateTimeField(null=True, auto_now_add=True)
    object_url = models.URLField(null=True, blank=True, max_length=10000)  # can be a URL to a post or comment

    # generic foreign key to attach like to Post or Comment
    # set default value to post content type
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, default=ContentType.objects.get_for_model(Post).id)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(max_length=200, null=True, blank=True) # for storing primary key value of the model itll be relating to
    content_object = GenericForeignKey('content_type', 'object_id') # foreign key to a Comment or Post

    def save(self, *args, **kwargs):
        # create url using the author's url and like id 
        if not self.url:
            self.url = f"{self.author_id.url.rstrip('/')}/liked/{self.id}/"
        super().save(*args, **kwargs)

    def __str__(self):
      return f'{self.author_id} like'
    
class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True, editable=False, blank=True, null=True) #identify comment by url
    author_id = models.ForeignKey('users.Author', on_delete=models.CASCADE, related_name='comments') 
    published = models.DateTimeField(auto_now_add=True)
    comment = models.TextField()
    post_id = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content_type = models.CharField(max_length=50, blank=True, null=True, default='text/plain')
    page = models.URLField(blank=True, null=True)

    # generic relation for reverse lookup for 'Like' objects on the post - because we are using generic foreign key in the like
    likes = GenericRelation('Like')

    def save(self, *args, **kwargs):
        # create url using the author's url and comment id 
        if not self.url:
            self.url = f"{self.author_id.url.rstrip('/')}/commented/{self.id}/"
        super().save(*args, **kwargs)
    
    def __str__(self):
      return f'{self.author_id} commented on {self.post_id}'
    
    class Meta:
        ordering = ['-published']
    