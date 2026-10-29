import base64
import logging
import re
import requests

from users.utils import is_fqid, is_request_author, get_request_author, are_friends, parse_uuid
from users.models import Author
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from .models import Post, Comment, Like
from .serializers import PostSerializer, CommentSerializer, LikeSerializer, with_post_relations
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from users.models import Follows
from .pagination import LikesPagination, CustomPostsPagination
import urllib.parse  # asked chatGPT how to decode the URL-encoded FQID 2024-11-02
from django.http import FileResponse
from django.conf import settings
from django.core.cache import cache
from django.db import transaction #transaction requests so that if something happens in the middle, it'll be rolled back

logger = logging.getLogger(__name__)

# The home feed shows at most this many of the newest posts
FEED_POST_LIMIT = 100



#region Post Views

def can_view_post(request, post):
    '''
    Public, unlisted and shared posts are visible to everyone; friends-only posts
    to the author and their friends; deleted posts only to the author.
    '''
    if post.visibility in ('PUBLIC', 'UNLISTED', 'SHARED'):
        return True
    viewer = get_request_author(request)
    if viewer is None:
        return False
    if viewer.id == post.author_id_id:
        return True
    return post.visibility == 'FRIENDS' and are_friends(viewer, post.author_id)


class PostDetailsView(APIView):
    """
    Retrieve, update or delete a post instance by author ID & post ID.
    """
    
    def get(self, request, author_serial, post_serial):
        """
        Retrieve a post instance by author ID & post ID.
        """
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            # check if post_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
            if is_fqid(post_serial):
                post_serial = urllib.parse.unquote(post_serial)
                if not post_serial.endswith("/"):
                    post_serial += "/"
                post_serial = Post.objects.get(url=post_serial).id
            post = Post.objects.get(id=post_serial, author_id=author_serial)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Get related objects for comments and likes
        comments = post.comments.all()
        likes = post.likes.all()

        # Get the author of the post
        author = post.author_id
        
        # Prepare the post data with dynamic links from the database
        post_data = {
            "type": "post",
            "title": post.title,
            "id": post.url,
            "description": post.description,
            "contentType": post.content_type,
            "content": post.content,
            "author": {
                "type": "author",
                "id": author.url,
                "host": author.host,
                "displayName": author.display_name,
                "page": author.page,
                "github": author.github,
                "profileImage": author.profile_image
            },
            "comments": {
                "type": "comments",
                "page": post.url,  # Page URL for the comments
                "id": post.url + "/comments",  # Custom URL for comments
                "page_number": 1,
                "size": len(comments),
                "count": post.comments.count(),
                "src": []
            },
            "likes": {
                "type": "likes",
                "page": post.url,  # Likes page URL
                "id": post.url + "/likes",  # Custom URL for likes
                "page_number": 1,
                "size": len(likes),
                "count": post.likes.count(),
                "src": []
            },
            "published": post.published.isoformat(),
            "visibility": post.visibility
        }

        # Collect comments data
        for comment in comments:
            comment_data = {
                "type": "comment",
                "author": {
                    "type": "author",
                    "id": comment.author_id.url,
                    "page": comment.author_id.page,
                    "host": comment.author_id.host,
                    "displayName": comment.author_id.display_name,
                    "github": comment.author_id.github,
                    "profileImage": comment.author_id.profile_image
                },
                "comment": comment.comment,
                "contentType": comment.content_type,
                "published": comment.published.isoformat(),
                "id": comment.url,
                "post": post.url,
                "page": comment.page,
            }
            post_data["comments"]["src"].append(comment_data)

        # Collect likes data
        for like in likes:
            like_data = {
                "type": "like",
                "author": {
                    "type": "author",
                    "id": like.author_id.url,
                    "page": like.author_id.page,
                    "host": like.author_id.host,
                    "displayName": like.author_id.display_name,
                    "github": like.author_id.github,
                    "profileImage": like.author_id.profile_image
                },
                "published": like.published.isoformat(),
                "id": like.url,
                "object": post.url
            }
            post_data["likes"]["src"].append(like_data)

        return Response(post_data)
      
    def put(self, request, author_serial, post_serial):
        """
        Update a post instance by author ID & post ID.
        """
        with transaction.atomic():
            try:
                # check if author_serial is a URL (FQID) or a uuid (SERIAL)
                # check if post_serial is a URL (FQID) or a uuid (SERIAL)
                if is_fqid(author_serial):
                    author_serial = urllib.parse.unquote(author_serial)
                    if not author_serial.endswith("/"):
                        author_serial += "/"
                    author_serial = Author.objects.get(url=author_serial).id
                if is_fqid(post_serial):
                    post_serial = urllib.parse.unquote(post_serial)
                    if not post_serial.endswith("/"):
                        post_serial += "/"
                    post_serial = Post.objects.get(url=post_serial).id
            except:
                return Response({"error": "PostDetailsView - PUT - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
            
            # get the post instance
            try:
                old_post = Post.objects.get(id=post_serial, author_id=author_serial)
            except Post.DoesNotExist:
                return Response({"error": f"Post {post_serial} not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # get the author instance
            try:
                author = Author.objects.get(id=author_serial)
            except Author.DoesNotExist:
                return Response({"error": f"Author {author_serial} not found."}, status=status.HTTP_404_NOT_FOUND)

            if not is_request_author(request, author.id):
                return Response({"error": "You can only edit your own posts."}, status=status.HTTP_403_FORBIDDEN)
            
            # serialize the updated post
            serializer = PostSerializer(old_post, data=request.data)
            # update post locally
            if serializer.is_valid():
                serializer.save(author_id=author)
            else:
                return Response({"error": f"Couldn't update the post: {serializer.errors}"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        

class PostDetailsByFqidView(APIView):
    """
    Retrieve post by Fully Qualified ID (URL + ID), or by its SERIAL (used by shared post links).
    """

    def get(self, request, post_fqid):
        post_ref = urllib.parse.unquote(post_fqid)
        if is_fqid(post_ref):
            post = Post.objects.filter(url=post_ref).first() or Post.objects.filter(url=post_ref.rstrip('/') + '/').first()
        else:
            post = Post.objects.filter(id=parse_uuid(post_ref.strip('/'))).first()
        if post is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # same shape as posts in the feed (ids without a trailing slash, plus like/comment
        # counts), so the shared post page renders exactly like a feed card
        viewer = get_request_author(request)
        post = with_post_relations(Post.objects.filter(id=post.id)).get()
        return Response(PostSerializer(post, context={'viewer_id': viewer.id if viewer else None}).data)


class AuthorPostsView(APIView):
    """
    List all posts by an author, or create a new post for the author.
    """
    pagination_class = CustomPostsPagination

    def get(self, request, author_serial):
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
        except:
            return Response({"error": "AuthorPostsView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        posts = [
            post for post in with_post_relations(Post.objects.filter(author_id=author_serial))
            if can_view_post(request, post)
        ]

        all_post_data = []

        # Loop through each post and format it
        for post in posts:
            comments = post.comments.all()
            likes = post.likes.all()

            # Prepare the post data with dynamic links from the database
            post_data = {
                "type": "post",
                "title": post.title,
                "id": post.url,
                "description": post.description,
                "contentType": post.content_type,
                "content": post.content,
                "author": {
                    "type": "author",
                    "id": post.author_id.url,
                    "host": post.author_id.host,
                    "displayName": post.author_id.display_name,
                    "page": post.author_id.page,
                    "github": post.author_id.github,
                    "profileImage": post.author_id.profile_image
                },
                "comments": {
                    "type": "comments",
                    "page": post.url,  # Page URL for the comments
                    "id": post.url + "/comments",  # Custom URL for comments
                    "page_number": 1,
                    "size": len(comments),
                    "count": post.comments.count(),
                    "src": []
                },
                "likes": {
                    "type": "likes",
                    "page": post.url,  # Likes page URL
                    "id": post.url + "/likes",  # Custom URL for likes
                    "page_number": 1,
                    "size": len(likes),
                    "count": post.likes.count(),
                    "src": []
                },
                "published": post.published.isoformat(),
                "visibility": post.visibility
            }

            # Collect comments data
            for comment in comments:
                comment_data = {
                    "type": "comment",
                    "author": {
                        "type": "author",
                        "id": comment.author_id.url,
                        "page": comment.author_id.page,
                        "host": comment.author_id.host,
                        "displayName": comment.author_id.display_name,
                        "github": comment.author_id.github,
                        "profileImage": comment.author_id.profile_image
                    },
                    "comment": comment.comment,
                    "contentType": comment.content_type,
                    "published": comment.published.isoformat(),
                    "id": comment.url,
                    "post": post.url,
                    "page": comment.page,
                }
                post_data["comments"]["src"].append(comment_data)

            # Collect likes data
            for like in likes:
                like_data = {
                    "type": "like",
                    "author": {
                        "type": "author",
                        "id": like.author_id.url,
                        "page": like.author_id.page,
                        "host": like.author_id.host,
                        "displayName": like.author_id.display_name,
                        "github": like.author_id.github,
                        "profileImage": like.author_id.profile_image
                    },
                    "published": like.published.isoformat(),
                    "id": like.url,
                    "object": post.url
                }
                post_data["likes"]["src"].append(like_data)

            # Append the post data to the response list
            all_post_data.append(post_data)

        # Hardcoded response format
        response_data = {
            "type": "posts",
            "page_number": 1,  # Hardcoding to 1 since no pagination
            "size": len(posts),  # Total posts as size
            "count": len(posts),  # Total posts count
            "src": all_post_data  # List of all posts
        }

        return Response(response_data)


    def post(self, request, author_serial):
        '''
        create a post for the author
        '''
        with transaction.atomic(): #a lot of datbase operations, better to do transaction so that if something fails, we can rollback instead of half updates
            try:
                # check if author_serial is a URL (FQID) or a uuid (SERIAL)
                if is_fqid(author_serial):
                    author_serial = urllib.parse.unquote(author_serial)
                    if not author_serial.endswith("/"):
                        author_serial += "/"
                    author_serial = Author.objects.get(url=author_serial).id
            except:
                return Response({"error": "AuthorPostsView - POST - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
            
            # create post locally first 
            try:
                author = Author.objects.get(id=author_serial)
            except Author.DoesNotExist:
                return Response({"error": f"Author {author_serial} not found."}, status=status.HTTP_404_NOT_FOUND)

            if not is_request_author(request, author.id):
                return Response({"error": "You can only create posts as yourself."}, status=status.HTTP_403_FORBIDDEN)

            serializer = PostSerializer(data=request.data)
            # create post locally
            if serializer.is_valid():
                serializer.save(author_id=author)  # Associate the post with the author
            else:
                return Response({"error": f"Couldn't create the post: {serializer.errors}"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
      
class PostImageView(APIView):
    """
    Retrieve the image of a post if available.
    """
    # permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, author_serial, post_serial):
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            # check if post_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
            if is_fqid(post_serial):
                post_serial = urllib.parse.unquote(post_serial)
                if not post_serial.endswith("/"):
                    post_serial += "/"
                post_serial = Post.objects.get(url=post_serial).id
        except:
            return Response({"error": "PostImageView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        author = get_object_or_404(Author, id=author_serial)
        post = get_object_or_404(Post, author_id=author, id=post_serial)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not post.content_type.startswith('image/'):
            return Response({'detail': 'No image available for this post'}, status=status.HTTP_404_NOT_FOUND)

        try:
            encoded_image = post.content

            missing_padding = len(encoded_image) % 4
            if missing_padding:
                encoded_image += '=' * (4 - missing_padding)
            encoded_image = re.sub(r"\s+", "", encoded_image)
            binary_image = base64.b64decode(encoded_image)

            # return Response(binary_image, content_type=post.content_type)
            return FileResponse(binary_image, content_type=post.content_type)
        except Exception as e:
            print(f"Error decoding image: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicPostsView(APIView):
    # The home feed: every post the current author is allowed to see, newest first
    permission_classes = [IsAuthenticatedOrReadOnly] 

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided to get public posts."}, status=status.HTTP_403_FORBIDDEN)

        current_author = get_object_or_404(Author, user=request.user)

        # - following_ids: set of IDs of authors that the current author follows
        # - followers_ids: set of IDs of authors that follow the current author
        following_ids = set(Follows.objects.filter(local_follower_id=current_author, status='ACCEPTED').values_list('followed_id', flat=True))
        followers_ids = set(Follows.objects.filter(followed_id=current_author, status='ACCEPTED').values_list('local_follower_id', flat=True))
        mutual_friend_ids = following_ids.intersection(followers_ids)

        # public posts from everyone, unlisted/shared posts from people you follow,
        # friends-only posts from mutual friends, and all of your own posts.
        # Filtering in the query keeps the limit counting only posts the viewer can see.
        visible = (
            Q(visibility='PUBLIC')
            | Q(visibility__in=['UNLISTED', 'SHARED'], author_id__in=following_ids)
            | Q(visibility='FRIENDS', author_id__in=mutual_friend_ids)
            | Q(author_id=current_author)
        )
        # newest posts first (Post.Meta.ordering); deleted posts are never shown in the feed
        posts = with_post_relations(Post.objects.filter(visible).exclude(visibility='DELETED'))[:FEED_POST_LIMIT]

        serializer = PostSerializer(posts, many=True, context={'viewer_id': current_author.id})
        return Response({'posts': serializer.data}, status=status.HTTP_200_OK)
    
#endregion

#region Comment Views
class CommentedView(APIView):
    """
    get, comment on post
    """
    def post(self, request, author_serial):
        """
        Comment on a post
        """
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
        except:
            return Response({"error": "CommentedView - POST - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        #author who created the comment
        author = get_object_or_404(Author, id=author_serial)
        if not is_request_author(request, author.id):
            return Response({"error": "You can only comment as yourself."}, status=status.HTTP_403_FORBIDDEN)
       
        comment_data = request.data
        request_type = comment_data.get('type')

        if request_type != 'comment':
            return Response({"detail": "Must be 'comment' type"}, status=status.HTTP_400_BAD_REQUEST)
        
        post_url = comment_data.get("post")
        if not post_url:
            return Response({"Error": "Post URL is required."}, status=status.HTTP_400_BAD_REQUEST)

        post_id = post_url.rstrip('/').split("/posts/")[-1]
        post = get_object_or_404(Post, id=post_id)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        #creating the comment object locally
        comment_serializer = CommentSerializer(data=request.data)
        if comment_serializer.is_valid():
            comment_serializer.save(
                author_id=author,
                post_id=post
            )
        else:
            return Response(comment_serializer.errors, status=status.HTTP_400_BAD_REQUEST) 

        return Response(comment_serializer.data, status=status.HTTP_201_CREATED)   
        
        
    def get(self, request, author_serial):
        """ 
        Get the list of comments author has made on any post [local]
        """
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
        except:
            return Response({"error": "CommentedView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        author = get_object_or_404(Author, id=author_serial)

        # leave out comments on posts this viewer can't see (e.g. someone else's friends-only post)
        comments = [
            comment for comment in author.comments.select_related('post_id').order_by('-published')
            if can_view_post(request, comment.post_id)
        ]

        serializer = CommentSerializer(comments, many=True) # many=True specifies that input is not just a single comment
        #host is the host of commenter
        host = author.host.rstrip('/')

        response_data = {
            "type": "comments",
            "page": f"{host}/authors/{author_serial}",
            "id": f"{host}/authors/{author_serial}",
            "page_number": 1,
            "size": len(comments),
            "count": len(comments),
            "src": serializer.data  
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class CommentsByAuthorFQIDView(APIView):
    """
    Get the list of comments author has made on any post
    """
    def get(self, request, author_fqid):
        decoded_fqid = urllib.parse.unquote(author_fqid)

        # example author fqid: http://localhost/api/authors/1d6dfebf-63a6-47a9-8e88-5cda73675db5/
        try:
            parts = decoded_fqid.split('/')
            author_serial = parts[parts.index('authors') + 1] 
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        author = get_object_or_404(Author, id=author_serial)

        # leave out comments on posts this viewer can't see (e.g. someone else's friends-only post)
        comments = [
            comment for comment in author.comments.select_related('post_id').order_by('-published')
            if can_view_post(request, comment.post_id)
        ]

        serializer = CommentSerializer(comments, many=True) # many=True specifies that input is not just a single comment
        #host is the host of commenter
        host = author.host.rstrip('/')

        response_data = {
            "type": "comments",
            "page": f"{host}/authors/{author_serial}",
            "id": f"{host}/authors/{author_serial}",
            "page_number": 1,
            "size": len(comments),
            "count": len(comments),
            "src": serializer.data  
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class CommentView(APIView):
    """
    Get a single comment
    """
    def get(self, request, author_serial, comment_serial):
        """
        Get a single comment
        """
        try:
            # check if comment_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(comment_serial):
                comment_serial = urllib.parse.unquote(comment_serial)
                if not comment_serial.endswith("/"):
                    comment_serial += "/"
                comment_serial = Comment.objects.get(url=comment_serial).id
        except:
            return Response({"error": "CommentView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = get_object_or_404(Comment, id=comment_serial)
        # comments are only visible to people who can see the post
        if not can_view_post(request, comment.post_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class CommentsView(APIView):
    """
    get comments on a post
    """
    def get(self, request, author_serial, post_serial):
        """
        get comments on a post 
        """
        try:
            # check if post_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(post_serial):
                post_serial = urllib.parse.unquote(post_serial)
                if not post_serial.endswith("/"):
                    post_serial += "/"
                post_serial = Post.objects.get(url=post_serial).id
        except:
            return Response({"error": "CommentsView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        post = get_object_or_404(Post, id=post_serial)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        comments = post.comments.all().order_by('-published')

        serializer = CommentSerializer(comments, many=True) # many=True specifies that input is not just a single comment
        #host is the host from the post
        host = post.author_id.host.rstrip('/')
        post_author_id = post.author_id

        # "page":"http://nodebbbb/authors/222/posts/249",
        # "id":"http://nodebbbb/authors/222/posts/249/comments"
        response_data = {
            "type": "comments",
            "page": f"{host}/authors/{post_author_id}/posts/{post_serial}",
            "id": f"{host}/authors/{post_author_id}/posts/{post_serial}/comments",
            "page_number": 1,
            "size": post.comments.count(),
            "count": post.comments.count(),
            "src": serializer.data  
        }

        return Response(response_data, status=status.HTTP_200_OK)

class CommentsByFQIDView(APIView):
    """
    Get comments on a post by post FQID
    """
    def get(self, request, post_fqid):
        # example post url: http://nodebbbb/authors/222/posts/249
        #decoding fqid from chatGPT: asked chatGPT how to decode the FQID 2024-11-02
        decoded_fqid = urllib.parse.unquote(post_fqid)

        try:
            parts = decoded_fqid.split('/')
            author_id = parts[parts.index('authors') + 1] 
            post_serial = parts[parts.index('posts') + 1]      
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        post = get_object_or_404(Post, id=post_serial) 
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        comments = post.comments.all().order_by('-published')

        serializer = CommentSerializer(comments, many=True) # many=True specifies that input is not just a single comment
        #host is the host from the post
        host = post.author_id.host.rstrip('/')
        post_author_id = post.author_id.id

        # "page":"http://nodebbbb/authors/222/posts/249",
        # "id":"http://nodebbbb/api/authors/222/posts/249/comments"
        response_data = {
            "type": "comments",
            "page": f"{host}/authors/{post_author_id}/posts/{post_serial}",
            "id": f"{host}/authors/{post_author_id}/posts/{post_serial}/comments",
            "page_number": 1,
            "size": post.comments.count(),
            "count": post.comments.count(),
            "src": serializer.data  
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class CommentRemoteByFQIDView(APIView):
    """
    Get a comment by its FQID [local, remote]
    """
    def get(self, request, author_serial, post_serial, comment_fqid):
        """
        Get a comment by its FQID [local, remote]
        """
        #example comment url: http://nodeaaaa/api/authors/111/commented/130
        #decode comment fqid
        decoded_fqid = urllib.parse.unquote(comment_fqid)

        try:
            parts = decoded_fqid.split('/')
            author_id = parts[parts.index('authors') + 1] 
            comment_serial = parts[parts.index('commented') + 1]      
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = get_object_or_404(Comment, id=comment_serial)
        # comments are only visible to people who can see the post
        if not can_view_post(request, comment.post_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CommentByFQIDView(APIView):
    """
    get comment by comment fqid
    """
    def get(self, request, comment_fqid):
        """
        get comment by comment fqid
        """
        #example comment url: http://nodeaaaa/api/authors/111/commented/130
        #decode comment fqid
        decoded_fqid = urllib.parse.unquote(comment_fqid)

        try:
            parts = decoded_fqid.split('/')
            author_id = parts[parts.index('authors') + 1] 
            comment_serial = parts[parts.index('commented') + 1]      
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = get_object_or_404(Comment, id=comment_serial)
        # comments are only visible to people who can see the post
        if not can_view_post(request, comment.post_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
#endregion
    
#region Like views   
class LikedView(APIView):
    """
    get, like or unlike a post
    """
    def post(self, request, author_serial):
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
        except:
            return Response({"error": "LikedView - POST - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        #author who created the like
        author = get_object_or_404(Author, id=author_serial)
        if not is_request_author(request, author.id):
            return Response({"error": "You can only like as yourself."}, status=status.HTTP_403_FORBIDDEN)
       
        like_data = request.data
        request_type = like_data.get('type')

        if request_type != 'like':
            return Response({"detail: Must be 'like' type"}, status=status.HTTP_400_BAD_REQUEST)
        
        object_url = like_data.get("object") #object can be either a comment or post
        if not object_url:
            return Response({"Error": "object URL is required."}, status=status.HTTP_400_BAD_REQUEST)

        # determine like was for post or comment
        if "/posts/" in object_url:
            # object is a post
            object_id = object_url.rstrip('/').split("/posts/")[-1]
            liked_object = get_object_or_404(Post, id=object_id)
            if not can_view_post(request, liked_object):
                return Response(status=status.HTTP_404_NOT_FOUND)
            object_content_type = ContentType.objects.get_for_model(Post)
            object_url_remote = f"{liked_object.author_id.host.rstrip('/')}/authors/{liked_object.author_id.id}/posts/{object_id}"
        elif "/commented/" in object_url:
            # object is a comment
            object_id = object_url.rstrip('/').split("/commented/")[-1]
            liked_object = get_object_or_404(Comment, id=object_id)
            object_content_type = ContentType.objects.get_for_model(Comment)
            object_url_remote = f"{liked_object.author_id.host.rstrip('/')}/authors/{liked_object.author_id.id}/commented/{object_id}"
        else:
            return Response({"detail": "Invalid object URL format."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        #check if user has already liked the object
        existing_like = Like.objects.filter(
            author_id=author,
            object_url=object_url_remote
        ).first()

        if existing_like:
            return Response(LikeSerializer(existing_like).data, status=status.HTTP_200_OK) #if they've already liked, can't like again

        # create like object locally
        like_serializer = LikeSerializer(data=request.data) #asked chatGPT how to set the host in the serializer, need to add context 2024-11-02
        if like_serializer.is_valid():

            like_serializer.save(
                author_id=author,  
                object_id=object_id,
                content_type=object_content_type,
                object_url=object_url_remote
            )

        else:
            return Response(like_serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
        
        return Response(like_serializer.data, status=status.HTTP_201_CREATED)   

    def delete(self, request, author_serial):
        """
        Unlike a post or comment: removes this author's like on the object given as
        `object` (its URL) in the request body or query string.
        """
        author = get_object_or_404(Author, id=parse_uuid(author_serial))
        if not is_request_author(request, author.id):
            return Response({"error": "You can only remove your own likes."}, status=status.HTTP_403_FORBIDDEN)

        object_url = request.data.get("object") or request.query_params.get("object")
        if not object_url:
            return Response({"Error": "object URL is required."}, status=status.HTTP_400_BAD_REQUEST)

        if "/posts/" in object_url:
            object_id = parse_uuid(object_url.rstrip('/').split("/posts/")[-1])
            content_type = ContentType.objects.get_for_model(Post)
        elif "/commented/" in object_url:
            object_id = parse_uuid(object_url.rstrip('/').split("/commented/")[-1])
            content_type = ContentType.objects.get_for_model(Comment)
        else:
            return Response({"detail": "Invalid object URL format."}, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = Like.objects.filter(author_id=author, content_type=content_type, object_id=object_id).delete()
        if not deleted:
            return Response({"detail": "You haven't liked this."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def get(self, request, author_serial):
        """
        get list of likes by author_id
        """
        try:
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
        except:
            return Response({"error": "LikedView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        author = get_object_or_404(Author, id=author_serial)
        likes = author.likes.all()

        # Pagination setup
        paginator = LikesPagination()
        paginated_likes = paginator.paginate_queryset(likes, request)

        serializer = LikeSerializer(paginated_likes, many=True)  # many=True specifies that input is not just a single like

        host = request.get_host()
        response_data = {
            "type": "likes",
            "page": f"http://{host}/authors/{author_serial}",
            "id": f"http://{host}/authors/{author_serial}/liked",
            "page_number": paginator.page.number,
            "size": paginator.get_page_size(request),
            "count": author.likes.count(),
            "src": serializer.data  # List of serialized like data
        }

        return Response(response_data, status=status.HTTP_200_OK)

class LikeView(APIView):
    """
    Get a single like by author and like serial
    """
    def get(self, request, author_serial, like_serial):
        """
        Get a single like by author serial and like serial
        """
        try:
            # check if like_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(like_serial):
                like_serial = urllib.parse.unquote(like_serial)
                if not like_serial.endswith("/"):
                    like_serial += "/"
                like_serial = Like.objects.get(url=like_serial).id
        except:
            return Response({"error": "LikeView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        like = get_object_or_404(Like, id=like_serial)
        serializer = LikeSerializer(like)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LikesView(APIView):
    """
    get likes on a post
    """
    def get(self, request, author_serial, post_id):
        """
        Get likes on a post
        """
        try:
            # check if post_id is a URL (FQID) or a uuid (SERIAL)
            # check if author_serial is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_serial):
                author_serial = urllib.parse.unquote(author_serial)
                if not author_serial.endswith("/"):
                    author_serial += "/"
                author_serial = Author.objects.get(url=author_serial).id
            if is_fqid(post_id):
                post_id = urllib.parse.unquote(post_id)
                if not post_id.endswith("/"):
                    post_id += "/"
                post_id = Post.objects.get(url=post_id).id
        except:
            return Response({"error": "LikesView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        post = get_object_or_404(Post, id=post_id)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        likes = post.likes.select_related('author_id').order_by('-published')
        viewer = get_request_author(request)

        # Pagination setup
        paginator = LikesPagination()
        paginated_likes = paginator.paginate_queryset(likes, request)

        serializer = LikeSerializer(paginated_likes, many=True)  # many=True specifies that input is not just a single like

        host = request.get_host().rstrip('/')
        response_data = {
            "type": "likes",
            "page": f"http://{host}/authors/{author_serial}/posts/{post_id}",
            "id": f"http://{host}/authors/{author_serial}/posts/{post_id}/likes",
            "page_number": paginator.page.number,
            "size": paginator.get_page_size(request),
            "count": post.likes.count(),
            # likes are paginated, so tell the client directly whether the viewer has liked this post
            "liked_by_me": viewer is not None and post.likes.filter(author_id=viewer).exists(),
            "src": serializer.data  # List of serialized like data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class LikedCommentsView(APIView):
    """
    Get likes for a comment
    """
    def get(self, request, author_id, post_id, comment_id):
        """
        get likes for a comment
        """
        try:
            # check if author_id is a URL (FQID) or a uuid (SERIAL)
            # check if post_id is a URL (FQID) or a uuid (SERIAL)
            # check if comment_id is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_id):
                author_id = urllib.parse.unquote(author_id)
                if not author_id.endswith("/"):
                    author_id += "/"
                author_id = Author.objects.get(url=author_id).id
            if is_fqid(post_id):
                post_id = urllib.parse.unquote(post_id)
                if not post_id.endswith("/"):
                    post_id += "/"
                post_id = Post.objects.get(url=post_id).id
            if is_fqid(comment_id):
                comment_id = urllib.parse.unquote(comment_id)
                if not comment_id.endswith("/"):
                    comment_id += "/"
                comment_id = Comment.objects.get(url=comment_id).id
        except:
            return Response({"error": "LikedCommentsView - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        post = get_object_or_404(Post, id=post_id)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)
        comment = get_object_or_404(Comment, id=comment_id, post_id=post)

        likes = comment.likes.all().order_by('-published')

        # Pagination setup
        paginator = LikesPagination()
        paginated_likes = paginator.paginate_queryset(likes, request)

        serializer = LikeSerializer(paginated_likes, many=True)  # many=True specifies that input is not just a single like

        host = request.get_host().rstrip('/')
        response_data = {
            "type": "likes",
            "page": f"http://{host}/authors/{author_id}/commented/{comment_id}",
            "id": f"http://{host}/authors/{author_id}/commented/{comment_id}/likes",
            "page_number": paginator.page.number,
            "size": paginator.get_page_size(request),
            "count": comment.likes.count(),
            "src": serializer.data  
        }

        return Response(response_data, status=status.HTTP_200_OK)

class LikesViewByFQIDView(APIView):
    """
    Get likes by FQID
    """
    def get(self, request, post_fqid):
        """
        get likes for post with fqid
        """
        # example post url: http://nodebbbb/authors/222/posts/249
        #decoding fqid from chatGPT: asked chatGPT how to decode the FQID 2024-11-02
        # Decode the FQID
        decoded_fqid = urllib.parse.unquote(post_fqid)

        # Split the decoded FQID to extract author_id and post_id
        try:
            parts = decoded_fqid.split('/')
            author_id = parts[parts.index('authors') + 1] 
            post_id = parts[parts.index('posts') + 1]      
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        post = get_object_or_404(Post, id=post_id)
        if not can_view_post(request, post):
            return Response(status=status.HTTP_404_NOT_FOUND)

        likes = post.likes.all().order_by('-published')

        # Pagination setup
        paginator = LikesPagination()
        paginated_likes = paginator.paginate_queryset(likes, request)

        serializer = LikeSerializer(paginated_likes, many=True)  # many=True specifies that input is not just a single like

        host = request.get_host().rstrip('/')
        response_data = {
            "type": "likes",
            "page": f"http://{host}/authors/{author_id}/posts/{post_id}",
            "id": f"http://{host}/authors/{author_id}/posts/{post_id}/likes",
            "page_number": paginator.page.number,
            "size": paginator.get_page_size(request),
            "count": post.likes.count(),
            "src": serializer.data  # List of serialized like data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class LikeViewByFQIDView(APIView):
    """
    Get a single like
    """
    def get(self, request, like_fqid):
        """
        Get a single like 
        """
        # example like url http://nodeaaaa/api/authors/222/liked/255
        # Decode the FQID
        decoded_fqid = urllib.parse.unquote(like_fqid)

        # Split the decoded FQID to extract author_id and like_id
        try:
            parts = decoded_fqid.split('/')
            #author_id = parts[parts.index('authors') + 1] 
            like_id = parts[parts.index('liked') + 1]      
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        like = get_object_or_404(Like, id=like_id)
        serializer = LikeSerializer(like)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LikedFQIDView(APIView):
    """
    get list of likes from author with FQID
    """
    def get(self, request, author_fqid):
        """
        get list of likes from author with FQID
        """
        # example author url: http://nodeaaaa/api/authors/111
        decoded_fqid = urllib.parse.unquote(author_fqid)

        try:
            parts = decoded_fqid.split('/')
            author_serial = parts[parts.index('authors') + 1] 
        except (ValueError, IndexError):
            return Response({"error": "Invalid FQID format"}, status=status.HTTP_400_BAD_REQUEST)
        
        author = get_object_or_404(Author, id=author_serial)
        likes = author.likes.all()

        # Pagination setup
        paginator = LikesPagination()
        paginated_likes = paginator.paginate_queryset(likes, request)

        serializer = LikeSerializer(paginated_likes, many=True)  # many=True specifies that input is not just a single like

        host = request.get_host().rstrip('/')
        response_data = {
            "type": "likes",
            "page": f"http://{host}/authors/{author_serial}",
            "id": f"http://{host}/authors/{author_serial}/liked",
            "page_number": paginator.page.number,
            "size": paginator.get_page_size(request),
            "count": author.likes.count(),
            "src": serializer.data  # List of serialized like data
        }

        return Response(response_data, status=status.HTTP_200_OK)
#endregion

#region Github Vews
# GitHub usernames: letters, digits and single hyphens, up to 39 characters
GITHUB_USERNAME_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$')
GITHUB_EVENTS_CACHE_SECONDS = 15 * 60

class GitHubEventsView(APIView):
    """
    Get public GitHub events for a username.
    """

    def get(self, request, username):
        if not GITHUB_USERNAME_RE.match(username):
            return Response({'error': 'Invalid GitHub username.'}, status=status.HTTP_400_BAD_REQUEST)

        # GitHub allows only 60 unauthenticated requests per hour per IP, so cache each user's events
        cache_key = f'github-events:{username.lower()}'
        events = cache.get(cache_key)
        if events is not None:
            return Response(events, status=status.HTTP_200_OK)

        github_api_url = f'https://api.github.com/users/{username}/events/public'
        headers = {
            'Accept': 'application/vnd.github+json',
        }
        if settings.GITHUB_TOKEN:
            headers['Authorization'] = f'Bearer {settings.GITHUB_TOKEN}'

        try:
            response = requests.get(github_api_url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an error for bad responses
            events = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            # GitHub being down or rate limited shouldn't break the page; just show no activity
            logger.warning("Could not fetch GitHub events for %s: %s", username, e)
            return Response([], status=status.HTTP_200_OK)

        cache.set(cache_key, events, GITHUB_EVENTS_CACHE_SECONDS)
        return Response(events, status=status.HTTP_200_OK)
#endregion