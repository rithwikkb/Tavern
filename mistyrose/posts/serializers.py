from users.serializers import AuthorSerializer
from users.models import Author
from rest_framework import serializers
from .models import Post, Comment, Like
import importlib
from django.urls import reverse

def with_post_relations(queryset):
    """
    Load everything PostSerializer touches (author, comments with their authors
    and likes, likes with their authors) in a fixed number of queries instead of
    several per post.
    """
    return queryset.select_related('author_id').prefetch_related(
        'likes__author_id',
        'comments__author_id',
        'comments__post_id__author_id',
        'comments__likes__author_id',
    )

#region Comment Serializers        
class CommentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default='comment', read_only=True)
    # set by the view from the logged-in user, never taken from the request body
    author = AuthorSerializer(source='author_id', read_only=True)
    id = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    post = serializers.SerializerMethodField()
    contentType = serializers.CharField(source='content_type', default='text/markdown', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'type',
            'id',
            'author',
            'published',
            'comment',
            'post',
            'contentType',
            'likes',
        ]

    def get_id(self, comment_object): #get is for turning into JSON response "id": "http://nodeaaaa/api/authors/111/commented/130"
        author_host = comment_object.author_id.host.rstrip('/')
        return f"{author_host}/authors/{comment_object.author_id.id}/commented/{comment_object.id}"
    
    def get_post(self, comment_object):
        post_id = comment_object.post_id.id
        post_author = comment_object.post_id.author_id
        post_author_host = post_author.host.rstrip('/')
        post_author_id = post_author.id
        return f"{post_author_host}/authors/{post_author_id}/posts/{post_id}" #"http://nodebbbb/api/authors/222/posts/249"
    
    def get_likes(self, comment_object):
        # sort in Python so prefetched likes are reused instead of re-queried
        likes = sorted(comment_object.likes.all(), key=lambda like: like.published, reverse=True)

        serializer = LikeSerializer(likes, many=True)
        
        host = comment_object.author_id.host.rstrip('/')
        response_data = {
            "type": "likes",
            "page": f"{host}/authors/{comment_object.author_id.id}/commented/{comment_object.id}/likes",
            "id": f"{host}/authors/{comment_object.author_id.id}/commented/{comment_object.id}/likes",
            "page_number": 1,
            "size": len(likes),
            "count": len(likes),
            "src": serializer.data,  # List of serialized like data
        }
        
        return response_data
    
#endregion
        
#region Like Serializers
class LikeSerializer(serializers.ModelSerializer):
    type = serializers.CharField(default='like', read_only=True)
    #author = serializers.SerializerMethodField()
    # set by the view from the logged-in user, never taken from the request body
    author = AuthorSerializer(source='author_id', read_only=True)
    object = serializers.SerializerMethodField() # calls get_object with current Like instance to set the object url
    id = serializers.SerializerMethodField()
    class Meta:
        model = Like
        fields = [
            'type',
            'author',
            'published',
            'id',
            'object',
        ]

    #asked chatGPT how to set the host in the serializer, need to send context from the view and call it as shown 2024-11-02
    def get_id(self, like_object): #get is for turning into JSON response
        author_host = like_object.author_id.host.rstrip('/')
        return f"{author_host}/authors/{like_object.author_id.id}/liked/{like_object.id}"


    def get_object(self, like_object):
        return like_object.object_url

#region Post Serializers
class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source='author_id', read_only=True)
    #author = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), write_only=True, source='author_id')
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)
    contentType = serializers.CharField(source='content_type', default='text/plain')
    #original_url = serializers.ListField(child=serializers.CharField(), allow_null=True, required=False)
    description = serializers.CharField(required=False, default='No Description', allow_null=True, allow_blank=True)

    class Meta:
        model = Post
        fields = [
            'type',
            'title',
            'id',
            'description',
            'contentType',
            'content',
            'author',
            'comments',
            'likes',
            'published',
            'visibility',
            #'original_url',
        ]

       
        # Method to get likes count for a post
    def get_likes_count(self, post):
        return Like.objects.filter(object_id=post.id).count()

    # Method to get comments count for a post
    def get_comments_count(self, post):
        return Comment.objects.filter(post_id=post.id).count()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # (already serialized as `author` via source='author_id')
        if representation['description'] is None:
            representation['description'] = 'No Description' 
        
        # if instance.content_type.startswith('image/'):
        #     representation['content'] = f"data:{instance.content_type};base64,{instance.content}"
        
        # get id for post
        representation['id'] = self.get_id(instance)

        # summary fields so the post cards don't need extra requests
        likes = instance.likes.all()
        representation['likes_count'] = len(likes)
        representation['comments_count'] = len(instance.comments.all())
        viewer_id = self.context.get('viewer_id')
        if viewer_id is not None:
            representation['liked_by_me'] = any(like.author_id_id == viewer_id for like in likes)
        
        return representation
    
    def get_id(self, post_object): #get is for turning into JSON response
        author_host = post_object.author_id.host.rstrip('/')
        return f"{author_host}/authors/{post_object.author_id.id}/posts/{post_object.id}"
    
#endregion
    
    # def get_author(self, like_object): #TODO: remove - this is temporary fix to circular dependency in AuthorSerializer importing PostSerializer
    #     AuthorSerializer = get_author_serializer()
    #     return AuthorSerializer(like_object.author_id).data

# class LikesSerializer(serializers.Serializer): 
#     type = serializers.CharField(default='likes', read_only=True)
#     page = serializers.SerializerMethodField()
#     id = serializers.SerializerMethodField()
#     page_number = serializers.IntegerField(default=1)
#     size = serializers.IntegerField()
#     count = serializers.IntegerField()
#     src = LikeSerializer(many=True)  # Use your existing LikeSerializer to serialize the likes

#     def get_page(self, obj):
#         # Construct the page URL; customize as needed
#         return f"http://localhost/api/authors/{obj.author_id.id}/commented/{obj.id}/likes"

#     def get_id(self, obj):
#         author_host = obj.author_id.host.rstrip('/')
#         http://{host}/api/authors/{author_serial}/posts/{post_id}/likes
#         return f"{author_host}/api/authors/{obj.author_id.id}/posts/{like_object.id}/likes"
#         return f"http://localhost/api/authors/{obj.author_id.id}/commented/{obj.id}/likes"
    
#endregion