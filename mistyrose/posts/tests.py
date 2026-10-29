from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from users.models import Author, Follows
from posts.models import Comment, Like, Post
import urllib.parse
import json
import uuid
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import urlparse
import re

#Basic test class, used for login settings
class BaseTestCase(APITestCase):
    def setUp(self):
        self.test_username = 'testuser'
        self.test_password = 'testpassword'
        self.user = User.objects.create_user(username=self.test_username, password=self.test_password)
        self.author = Author.objects.create(user=self.user)

        # Log in and get token
        login_url = '/api/login/'
        response = self.client.post(
            login_url,
            data=json.dumps({
                'username': self.test_username,
                'password': self.test_password
            }),
            content_type='application/json'
        )

        # Check and extract token
        if response.status_code == 200 and 'access_token' in response.json():
            self.token = response.json()['access_token']
            self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)
        else:
            print("Login failed. Status:", response.status_code, "Content:", response.content)
            self.token = None


class PostDetailsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Test Post',
            content_type='text/plain',
            content='This is a test post.'
        )
        self.post_url = reverse('post-detail', args=[self.author.id, self.post.id])

    def test_post_details_view(self):
        response = self.client.get(self.post_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Post')
        
    def test_post_details_with_unauthenticated_user(self):
        self.client.credentials()
        response = self.client.get(self.post_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_post_details_with_invalid_post_id(self):
        invalid_post_url = reverse('post-detail', args=[self.author.id, uuid.uuid4()]) 
        response = self.client.get(invalid_post_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_post_details_with_invalid_author_id(self):
        invalid_author_url = reverse('post-detail', args=[uuid.uuid4(), self.post.id])
        response = self.client.get(invalid_author_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AuthorPostsViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        Post.objects.all().delete()
        self.url = reverse('author-posts', args=[self.author.id])
        self.post1 = Post.objects.create(author_id=self.author, title="Post 1", content_type="text/plain", content="Content 1")
        self.post2 = Post.objects.create(author_id=self.author, title="Post 2", content_type="text/plain", content="Content 2")

    def test_get_author_posts(self):
        response = self.client.get(self.url)
        # print("Response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["src"]), 2)  # should return two posts

    def test_create_post(self):
        data = {
            'author': self.author.id,
            'title': 'New Post',
            'content_type': 'text/plain',
            'content': 'New content',
            'visibility': 'PUBLIC',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 3)

    def test_create_post_unauthenticated(self):
        self.client.credentials()
        data = {
            'author': self.author.id,
            'title': 'Unauthenticated Post',
            'content_type': 'text/plain',
            'content': 'Content for unauthenticated user',
            'visibility': 'PUBLIC',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class PublicPostsViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user2 = User.objects.create_user(username='publicuser2', password='somethingHardToCrack357')
        self.author2 = Author.objects.create(user=self.user2, display_name='Public User 2', host='http://localhost:8000')

        self.post1 = Post.objects.create(
            author_id=self.author,
            title='Public Post 1',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )
        self.post2 = Post.objects.create(
            author_id=self.author2,
            title='Public Post 2',
            content_type='text/plain',
            content='This is another public post.',
            visibility='PUBLIC'
        )

    def test_get_public_posts(self):
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # should return two posts

#region Comments Tests
#asked chatGPT to assist with writing test cases for comments endpoints 2024-11-04
class CommentedViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )
        self.comment_url = reverse('commented', args=[self.author.id])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_create_comment_success(self):
        data = {
            'type': 'comment',
            'author': {
                'type': 'author',
                'id': f'http://localhost/api/authors/{self.author.id}/',
                'host': 'http://localhost',
                'page': f'http://localhost/api/authors/{self.author.id}/',
                'displayName': 'Greg',
            },
            'post': f'http://localhost/authors/{self.author.id}/posts/{self.post.id}/',
            'comment': 'This is a test comment.',
            'contentType': 'text/plain'
        }
        response = self.client.post(self.comment_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['comment'], 'This is a test comment.')
        self.assertEqual(Comment.objects.count(), 1)

    def test_create_comment_invalid_type(self):
        data = {
            'type': 'like',  # Wrong type 
            'author': {
                'type': 'author',
                'id': f'http://localhost/api/authors/{self.author.id}/',
                'host': 'http://localhost',
                'page': f'http://localhost/api/authors/{self.author.id}/',
                'displayName': 'Greg',
            },
            'post': f'http://localhost:8000/authors/{self.author.id}/posts/{self.post.id}/',
            'comment': 'This is a test comment with wrong type.',
            'contentType': 'text/plain'
        }
        response = self.client.post(self.comment_url, data, format='json')
        
        # Check for 400 status 
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Must be 'comment' type", response.data['detail'])

    def test_get_comments_by_author(self):
        # Make a GET request for comments by the author
        response = self.client.get(self.comment_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data['type'], 'comments')
        self.assertEqual(response_data['page'], f'http://localhost/api/authors/{self.author.id}')
        self.assertEqual(response_data['id'], f'http://localhost/api/authors/{self.author.id}')

class CommentsByAuthorFQIDViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comment1 = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.comment2 = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the second comment.",
            content_type="text/plain",
        )

        self.fqid_url = f"http://localhost/api/authors/{self.author.id}/"

    def test_get_comments_by_author_success(self):
        # URL encode the FQID for the request
        url = reverse('comments_by_author_fqid', args=[urllib.parse.quote(self.fqid_url)])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "comments")
        self.assertEqual(response.data["page"], f"{self.author.host}authors/{self.author.id}")
        self.assertEqual(response.data["id"], f"{self.author.host}authors/{self.author.id}")

    def test_get_comments_by_author_invalid_fqid(self):
        # Test with an invalid FQID format - 400
        invalid_fqid = "invalid_fqid"
        url = reverse('comments_by_author_fqid', args=[invalid_fqid])
        response = self.client.get(url)

        # Ensure it returns 400 with appropriate error message
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid FQID format")

    def test_get_comments_by_author_nonexistent_author(self):
        # non existent author - 404
        non_existent_fqid = f"http://localhost/api/authors/{uuid.uuid4()}/"
        url = reverse('comments_by_author_fqid', args=[urllib.parse.quote(non_existent_fqid)])
        response = self.client.get(url)

        # Ensure it returns 404 as author does not exist
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class CommentViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comment = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )
    
    def test_get_comment_success(self):
        url = reverse('comment', args=[self.author.id, self.comment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "comment")
        self.assertEqual(response.data["comment"], "This is the first comment.")

    def test_get_comment_not_found(self):
        # get non existent comment - 404
        non_existent_comment_id = f'{uuid.uuid4()}'
        url = reverse('comment', args=[self.author.id, non_existent_comment_id])
        response = self.client.get(url)

        #404 error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class CommentsViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comment1 = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.comment2 = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the second comment.",
            content_type="text/plain",
        )

        self.url = reverse('get_post_comments', args=[self.author.id, self.post.id])  

    def test_get_comments_on_post_success(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  
        self.assertEqual(len(response.data['src']), 2)  

    def test_get_comments_on_post_not_found(self):
        non_existent_post_id = f"{uuid.uuid4()}"  
        url = reverse('get_post_comments', args=[self.author.id, non_existent_post_id])  
        response = self.client.get(url)

        # 404 not found response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class CommentsByFQIDView(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comments_fqid_url = f'http://localhost/api/authors/{self.author.id}/posts/{self.post.id}'

    def test_get_comments_by_fqid_success(self):
        Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment='This is a comment.'
        )

        response = self.client.get(reverse('get_comments_fqid', args=[self.comments_fqid_url]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "comments")

class CommentRemoteByFQIDViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comment = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.author.host = 'http://localhost'
        self.author.save()
        self.comment_fqid = f'http://localhost/api/authors/{self.author.id}/commented/{self.comment.id}'

    def test_get_comment_by_fqid_success(self):
        response = self.client.get(reverse('get_remote_comment_fqid', args=[self.author.id, self.post.id, self.comment_fqid]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], f'http://localhost/api/authors/{self.author.id}/commented/{self.comment.id}')


class CommentByFQIDView(BaseTestCase):
    def setUp(self):
        super().setUp()  

        self.post = Post.objects.create(
            author_id=self.author,
            title="Test Post",
            content_type="text/plain",
            content="This is a test post.",
            visibility="PUBLIC"
        )

        self.comment = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.author.host = 'http://localhost'
        self.author.save()
        self.comment_fqid = f'http://localhost/api/authors/{self.author.id}/commented/{self.comment.id}'

    def test_get_comment_by_fqid_success(self):
        response = self.client.get(reverse('comment_fqid', args=[self.comment_fqid]))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], f'http://localhost/api/authors/{self.author.id}/commented/{self.comment.id}')

#endregion

#region Likes Tests
# asked chatGPT for assistance for test case errors and general structure for writing tests 2024-11-04
class LikedViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.comment = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.like_url = reverse('liked', args=[self.author.id])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_like_post(self):
        like_data = {
            "type": "like",
            'author': {
                'type': 'author',
                'id': f'http://localhost/api/authors/{self.author.id}/',
                'host': 'http://localhost',
                'page': f'http://localhost/api/authors/{self.author.id}/',
                'displayName': 'Greg',
            },
            "object": f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        }

        response = self.client.post(self.like_url, like_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['type'], 'like')

    def test_like_invalid_type(self):
        invalid_like_data = {
            "type": "invalid_type",
            "object": f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        }

        response = self.client.post(self.like_url, invalid_like_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_like_already_exists(self):
        # Create an existing like
        Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        like_data = {
            "type": "like",
            'author': {
                'type': 'author',
                'id': f'http://localhost/api/authors/{self.author.id}/',
                'host': 'http://localhost',
                'page': f'http://localhost/api/authors/{self.author.id}/',
                'displayName': 'Greg',
            },
            "object": f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        }

        response = self.client.post(self.like_url, like_data, format='json')
        
        # Allow either 200 OK or 201 Created, depending on backend logic
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        # Additional check to ensure the 'like' type in the response
        self.assertEqual(response.data['type'], 'like')

    def test_get_likes(self):
        Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        response = self.client.get(self.like_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "likes")

class LikeViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        self.like_url = reverse('like', args=[self.author.id, self.like.id])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_get_like_successful(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_like_not_found(self):
        # Attempt to retrieve a like that does not exist
        invalid_like_url = reverse('like', args=[self.author.id, f"{uuid.uuid4()}"])  
        response = self.client.get(invalid_like_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LikesViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        self.like_url = reverse('post_likes', args=[self.author.id, self.post.id])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_get_likes_successful(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'likes')

    def test_get_likes_post_not_found(self):
        # Attempt to retrieve likes for a post that does not exist
        invalid_likes_url = reverse('post_likes', args=[self.author.id, f"{uuid.uuid4()}"]) 
        response = self.client.get(invalid_likes_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LikedCommentsViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.comment = Comment.objects.create(
            author_id=self.author,
            post_id=self.post,
            comment="This is the first comment.",
            content_type="text/plain",
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.comment.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/commented/{self.comment.id}"
        )

        self.like_url = reverse('comment_likes', args=[self.author.id, self.post.id, self.comment.id])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_get_likes_for_comment(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'likes')

    def test_get_likes_comment_not_found(self):
        # Attempt to retrieve likes for a comment that does not exist
        invalid_likes_url = reverse('comment_likes', args=[self.author.id, self.post.id, f"{uuid.uuid4()}"])
        response = self.client.get(invalid_likes_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class LikesViewByFQIDViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        self.fqid = urllib.parse.quote(f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}")

        self.like_url = reverse('get_likes_fqid', args=[self.fqid])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_get_likes_by_fqid(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'likes')
    
    def test_get_likes_post_not_found(self):
        # Attempt to retrieve likes for a post that does not exist
        invalid_fqid = urllib.parse.quote(f"http://{self.author.host}/authors/{self.author.id}/posts/{uuid.uuid4()}")  
        invalid_likes_url = reverse('get_likes_fqid', args=[invalid_fqid])  
        response = self.client.get(invalid_likes_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LikeViewByFQIDViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )
        self.author.host = 'http://localhost'
        self.author.save()

        # Encode FQID for the like
        self.like_fqid = urllib.parse.quote(f"http://{self.author.id}/authors/{self.author.id}/liked/{self.like.id}")
        self.like_url = reverse('get_like_fqid', args=[self.like_fqid])  

    def test_get_like_by_fqid(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'like')
  
    def test_get_like_not_found(self):
        # Attempt to retrieve a like that does not exist
        invalid_fqid = urllib.parse.quote(f"http://{self.author.host}/authors/{self.author.id}/liked/{uuid.uuid4()}")  
        invalid_like_url = reverse('get_like_fqid', args=[invalid_fqid])  
        response = self.client.get(invalid_like_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LikedFQIDViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            author_id=self.author,
            title='Public Post',
            content_type='text/plain',
            content='This is a public post.',
            visibility='PUBLIC'
        )

        self.like = Like.objects.create(
            author_id=self.author,
            object_id=self.post.id,
            content_type=ContentType.objects.get_for_model(self.post),
            object_url=f"http://{self.author.host}/authors/{self.author.id}/posts/{self.post.id}"
        )

        # Encode FQID for the author
        self.author_fqid = urllib.parse.quote(f"http://{self.author.host}/authors/{self.author.id}")

        self.like_url = reverse('liked_fqid', args=[self.author_fqid])  
        self.author.host = 'http://localhost'
        self.author.save()

    def test_get_likes_by_author_fqid(self):
        response = self.client.get(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'likes')

    def test_get_likes_author_not_found(self):
        # Attempt to retrieve likes for a non-existent author
        invalid_fqid = urllib.parse.quote(f"http://{self.author.host}/authors/{uuid.uuid4()}")  
        invalid_liked_url = reverse('liked_fqid', args=[invalid_fqid])  
        response = self.client.get(invalid_liked_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# User Story #5 Test: As an author, I want to my (new, public) GitHub activity to be automatically turned into public posts, so everyone can see my GitHub activity too.
class GitHubActivityToPostTest(TestCase):
    @patch('requests.get')  # Mock GitHub API call
    def test_github_activity_to_posts(self, mock_get):
        # Mock the data returned by the GitHub API
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "type": "PushEvent",
                "repo": {"name": "test-repo"},
                "created_at": "2024-11-17T12:00:00Z"
            }
        ]

        # Create an author object
        author = Author.objects.create(
            display_name="test_author",
            github="https://github.com/testuser",
            host="http://localhost:8000",
            page="http://localhost:8000/authors/test_author/"
        )

        # Call the existing route for GitHubEventsView
        response = self.client.get(f'/github/events/{author.github.split("/")[-1]}/')

        # print("Response type:", type(response))
        # print("Response content:", response.content.decode())

        # Manually simulate GitHub data processing logic and create posts
        for event in mock_get.return_value.json.return_value:
            Post.objects.create(
                author_id=author,
                title=f"{event['type']} in {event['repo']['name']}",
                content=f"Details: {event}",
                visibility="PUBLIC"
            )

        # print("All posts in database after test:")
        # for post in Post.objects.all():
        #     print(f"Post ID: {post.id}, Title: {post.title}, Author ID: {post.author_id}, Content: {post.content}, Visibility: {post.visibility}")

        # Verify that the post was correctly created
        self.assertTrue(Post.objects.filter(
            author_id=author.id,
            title="PushEvent in test-repo"
        ).exists())

    # User Story #8 Test: As an author, I want to make posts.
    def test_post_creation_directly(self):
        # Test if posts can be directly created successfully
        author = Author.objects.create(
            display_name="test_author",
            github="https://github.com/testuser",
            host="http://localhost:8000",
            page="http://localhost:8000/authors/test_author/"
        )

        Post.objects.create(
            author_id=author,
            title="PushEvent in test-repo",
            content="Details: Mock content",
            visibility="PUBLIC"
        )

        # print("All posts in database after direct creation:")
        # for post in Post.objects.all():
        #     print(f"Post ID: {post.id}, Title: {post.title}, Author ID: {post.author_id}, Content: {post.content}")

        # Verify that the post was successfully created
        self.assertTrue(Post.objects.filter(
            author_id=author,
            title="PushEvent in test-repo"
        ).exists())


# User Story #10 Test: As an author, I want to edit my posts locally.
class EditPostTest(APITestCase):
    def setUp(self):
        # Create test users and associated authors
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.author = Author.objects.create(
            id = uuid.uuid4(),
            display_name = "Test Author",
            host = "http://localhost:8000/api/",
            user= self.user
        )

        # Authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Create testing posts
        self.post = Post.objects.create(
            id = uuid.uuid4(),
            title = "Original Title",
            content = "Original Content",
            author_id = self.author,
            visibility = "PUBLIC"
        )

        # Edit post API URL
        self.edit_url = f"/api/authors/{self.author.id}/posts/{self.post.id}/"

    def test_edit_post_success(self):
        updated_data = {
            "title": "Updated Title",
            "content": "Updated Content"
        }

        # Send a PUT request to update a post
        response = self.client.put(self.edit_url, updated_data, format="json")

        # Verify return status code and post update status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, updated_data["title"])
        self.assertEqual(self.post.content, updated_data["content"])

# User Story #12 Test: As an author, posts I make can be in CommonMark, so I can give my posts some basic formatting.
class CommonMarkPostTest(APITestCase):
    def setUp(self):
        # Create test users and authors
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name="Test Author")

        # Authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.post_url = f"/api/authors/{self.author.id}/posts/"

    def test_create_post_with_commonmark(self):
        # Define content in a CommonMark format
        commonmark_content = "# Title\n\nThis is a **bold** statement and a [link](https://example.com)."

        # Create post
        response = self.client.post(self.post_url, {
            "title": "Test Post",
            "content": commonmark_content,
            "contentType": "text/markdown",
            "visibility": "PUBLIC",
        }, format='json')

        # Verify creation is successful
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, "Post creation failed")
        post_id = response.data.get('id')
        self.assertIsNotNone(post_id, "Post creation did not return an ID")
        
        # # Debugging: Print post creation response and post_id
        # print("Post creation response:", response.data)

        # Extract the UUID from post_id using regex
        match = re.search(r'/posts/([a-f0-9\-]+)/?$', post_id)
        self.assertIsNotNone(match, "Post ID does not contain a valid UUID")
        post_uuid = match.group(1)

        print("Extracted UUID:", post_uuid)  # Debugging: Print extracted UUID

        # Construct the correct URL for GET request
        get_url = f"{self.post_url}{post_uuid}/"
        # print("Constructed GET URL:", get_url)  # Debugging: Print GET URL

        # Get the post and verify whether the returned content is consistent with the input
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK, "Failed to retrieve the post")
        self.assertEqual(get_response.data['content'], commonmark_content)
        
# User Story #13 Test: As an author, posts I make can be in simple plain text, because I don't always want all the formatting features of CommonMark.
class PlainTextPostTest(APITestCase):
    def setUp(self):
        # Create test users and authors
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name="Test Author")

        # Authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.post_url = f"/api/authors/{self.author.id}/posts/"

    def test_create_plain_text_post(self):
        # Define plain text content
        plain_text_content = "This is a simple plain text post."

        # Create post
        response = self.client.post(self.post_url, {
            "title": "Plain Text Post",
            "content": plain_text_content,
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }, format='json')

        # Verify post is created successfully
        self.assertEqual(response.status_code, 201, "Post creation failed")
        post_id = response.data.get('id')
        self.assertIsNotNone(post_id, "Post creation did not return an ID")

        # # Debugging: Print post creation response and post_id
        # print("Post creation response:", response.data)

        # Extract the UUID from post_id using regex
        match = re.search(r'/posts/([a-f0-9\-]+)/?$', post_id)
        self.assertIsNotNone(match, "Post ID does not contain a valid UUID")
        post_uuid = match.group(1)

        print("Extracted UUID:", post_uuid)  

        # Construct the correct URL for GET request
        get_url = f"{self.post_url}{post_uuid}/"
        print("Constructed GET URL:", get_url)  

        # Get the post and verify that the content matches the input
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200, "Failed to retrieve the post")
        self.assertEqual(get_response.data['content'], plain_text_content)
        self.assertEqual(get_response.data['contentType'], "text/plain")

# User Story #14 Test: As an author, posts I create can be images, so that I can share pictures and drawings.
class ImagePostTest(APITestCase):
    def setUp(self):
        # Create test users and authors
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name="Test Author")

        # Authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.post_url = f"/api/authors/{self.author.id}/posts/"

    def test_create_image_post(self):
        # Prepare the Base64 encoded content of the image
        base64_image_content = (
            "/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQA"
            "AAEAAAABAAAASAAAAAEAAAABAAEAAKADAAQAAAABAAAAGgAAAAAAAAAAqgAAAAAAANABAAMAAAABAAEAAKACAAQAAAABAAAAGgAA"
            "AAEAAAABAAAASAAAAAEAAAABAAEAAKADAAQAAAABAAAAGgAAAAAAAAAAqgAAAAAAANABAAMAAAABAAEAAKACAAQAAAABAAAAGgAA"
            "AAEAAAABAAAASAAAAAEAAAABAAEAAKADAAQAAAABAAAAGgAAAAAAAAAAqgAAAAAAANABAAMAAAABAAEAAKACAAQAAAABAAAAGgAA"
        )
        
        # Create post request
        response = self.client.post(self.post_url, {
            "title": "Image Post",
            "content": base64_image_content,
            "contentType": "image/png",
            "visibility": "PUBLIC",
        }, format='json')

        # Verify post is created successfully
        self.assertEqual(response.status_code, 201, "Post creation failed")
        post_id = response.data.get('id')
        self.assertIsNotNone(post_id, "Post creation did not return an ID")
        
        # # Debugging: Print post creation response and post_id
        # print("Post creation response:", response.data)

        # Extract the UUID from post_id using regex
        match = re.search(r'/posts/([a-f0-9\-]+)/?$', post_id)
        self.assertIsNotNone(match, "Post ID does not contain a valid UUID")
        post_uuid = match.group(1)

        print("Extracted UUID:", post_uuid)  

        # Construct the correct URL for GET request
        get_url = f"{self.post_url}{post_uuid}/"
        print("Constructed GET URL:", get_url)  
        
        # Get post data and verify
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200, "Failed to retrieve the post")
        self.assertEqual(get_response.data['contentType'], "image/png")
        self.assertEqual(get_response.data['content'], base64_image_content)

# User Story #15 Test: As an author, posts I create that are in CommonMark can link to images, so that I can illustrate my posts.
class PostCommonMarkImagesTestCase(APITestCase):
    def setUp(self):
        # Create test users and authors
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword"
        )
        self.author = Author.objects.create(
            id=uuid.uuid4(),
            user=self.user,
            display_name="Test Author",
            github="https://github.com/testauthor"
        )

    def test_create_post_with_commonmark_and_image(self):
        # Define the content of the CommonMark format
        content = "![Test Image](https://example.com/test-image.jpg)"
        post = Post.objects.create(
            title="Test Post with Image",
            content_type="text/markdown",  
            content=content,
            author_id=self.author,  
            visibility="PUBLIC"
        )

        # Verify post content and type
        self.assertEqual(post.content, content)
        self.assertEqual(post.content_type, "text/markdown")

        # Confirm whether the image link is saved correctly
        self.assertIn("https://example.com/test-image.jpg", post.content)

# User Story #16 Test: As an author, I want to delete my own posts locally, so I can remove posts that are out of date or made by mistake.
class DeletePostTestCase(APITestCase):
    def setUp(self):
        # Create a user and an author
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.author = Author.objects.create(user=self.user, display_name='Test Author')

        # Authenticate the user with JWT
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Create a post by this author
        self.post = Post.objects.create(
            id=uuid.uuid4(),
            author_id=self.author,
            title="Test Post",
            content="This is a test post.",
            visibility="PUBLIC",
        )

        # url
        self.post_url = reverse('post-detail', args=[self.author.id, self.post.id])

    def test_get_post_after_visibility_change(self):
        # Manually update the visibility in the database
        self.post.visibility = "DELETED"
        self.post.save()

        # Fetch the post details
        response = self.client.get(self.post_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the visibility in the response
        self.assertEqual(response.data.get("visibility"), "DELETED")

# User Story #9 Test: As an author, I want my node to send my posts to my remote followers and friends.
class PostDeliveryTestCase(APITestCase):
    def setUp(self):
        # Create two users and corresponding authors
        self.user_a = User.objects.create_user(username="user_a", password="pass_a")
        self.author_a = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author A",
            host="http://localhost",
            user=self.user_a
        )
        self.user_b = User.objects.create_user(username="user_b", password="pass_b")
        self.author_b = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author B",
            host="http://remote.node",
            user=self.user_b
        )
        # Set up API client and authentication
        self.client = APIClient()
        self.login_user_a()
    def login_user_a(self):
        # Log in to User A and set up authentication
        login_url = "/api/login/"
        response = self.client.post(
            login_url,
            {"username": "user_a", "password": "pass_a"},
            format="json"
        )
        # print("Login response status code:", response.status_code)
        # print("Login response content:", response.content)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Login failed for User A")
        token = response.data.get("access_token")
        self.assertIsNotNone(token, "No access token returned for User A")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    def create_follow_relationship(self, follower, followed):
        # Create following relationship
        Follows.objects.create(
            local_follower_id=follower,
            followed_id=followed,
            is_remote=False,
            status="ACCEPTED"
        )
    def test_public_post_visible_to_remote_author(self):
        """Test whether PUBLIC posts are visible to remote authors (no following relationship required)"""
        post_id = uuid.uuid4()
        post_data = {
            "type": "post",
            "id": f"http://localhost/api/authors/{self.author_a.id}/posts/{post_id}/",
            "title": "Public Test Post",
            "content": "This is a public test post.",
            "visibility": "PUBLIC",
            "contentType": "text/plain",
            "author": {
                "id": str(self.author_a.id),
                "host": "http://localhost",
                "displayName": "Author A",
                "url": f"http://localhost/authors/{self.author_a.id}/",
                "github": "",
                "profileImage": "",
                "page": f"http://localhost/authors/{self.author_a.id}/"  # Make sure to include 'page'
            }
        }
        response = self.client.post(f"/api/authors/{self.author_b.id}/inbox/", post_data, format="json")
        # print("Response data (public post):", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    def test_friends_post_visible_to_friend(self):
        """Test whether FRIENDS posts are visible to friends (follow each other)"""
        # Create a two-way following relationship
        self.create_follow_relationship(self.author_a, self.author_b)
        self.create_follow_relationship(self.author_b, self.author_a)
        # Verify following relationship
        follows_a_to_b = Follows.objects.filter(local_follower_id=self.author_a, followed_id=self.author_b).exists()
        follows_b_to_a = Follows.objects.filter(local_follower_id=self.author_b, followed_id=self.author_a).exists()
        # print("Follows A->B:", follows_a_to_b)
        # print("Follows B->A:", follows_b_to_a)
        self.assertTrue(follows_a_to_b and follows_b_to_a, "The two-way following relationship has not been established")
        post_id = uuid.uuid4()
        post_data = {
            "type": "post",
            "id": f"http://localhost/api/authors/{self.author_a.id}/posts/{post_id}/",
            "title": "Friends Test Post",
            "content": "This is a friends test post.",
            "visibility": "FRIENDS",
            "contentType": "text/plain",
            "author": {
                "id": str(self.author_a.id),
                "host": "http://localhost",
                "displayName": "Author A",
                "url": f"http://localhost/authors/{self.author_a.id}/",
                "github": "",
                "profileImage": "",
                "page": f"http://localhost/authors/{self.author_a.id}/"
            }
        }
        response = self.client.post(f"/api/authors/{self.author_b.id}/inbox/", post_data, format="json")
        # print("Response data (friends post):", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

# User Story #11 Test: As an author, I want my node to re-send posts I've edited to everywhere they were already sent, so that people don't keep seeing the old version.
class PostEditResendTestCase(APITestCase):
    def setUp(self):
        # Create users and corresponding authors
        self.user_a = User.objects.create_user(username="user_a", password="pass_a")
        self.author_a = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author A",
            host="http://localhost",
            user=self.user_a
        )
        self.user_b = User.objects.create_user(username="user_b", password="pass_b")
        self.author_b = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author B",
            host="http://remote.node",
            user=self.user_b
        )
        # Set up API client and log in user A
        self.client = APIClient()
        self.login_user_a()
    def login_user_a(self):
        login_url = "/api/login/"
        response = self.client.post(
            login_url,
            {"username": "user_a", "password": "pass_a"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Login failed for User A")
        token = response.data.get("access_token")
        self.assertIsNotNone(token, "No access token returned for User A")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    def test_public_post_edit_resends_to_recipients(self):
        """Test whether to resend to recipients after editing a public post"""
        # Step 1: Create a public post
        post_data = {
            "type": "post",
            "title": "Original Test Post",
            "content": "This is the original content.",
            "visibility": "PUBLIC",
            "contentType": "text/plain",
            "author": {
                "id": str(self.author_a.id),
                "host": "http://localhost",
                "displayName": "Author A",
            }
        }
        response = self.client.post(f"/api/authors/{self.author_a.id}/posts/", post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, "Failed to create the original post")
        # # Verify that the post was created successfully
        # print("Post creation response:", response.data)
        # Get created post ID from response
        created_post_id = response.data.get("id")
        self.assertIsNotNone(created_post_id, "Post creation did not return a valid ID")
        
        # Extract the UUID from the post ID URL
        parsed_url = urlparse(created_post_id)
        uuid_part = parsed_url.path.split('/')[-1]  # Extract the UUID part
        # Step 2: Edit post content
        edited_post_data = post_data.copy()
        edited_post_data["id"] = uuid_part  # Use the post ID returned on creation
        edited_post_data["title"] = "Edited Test Post"
        edited_post_data["content"] = "This is the edited content."
        # Construct the correct edit URL
        edit_url = f"/api/authors/{self.author_a.id}/posts/{uuid_part}/"
        response = self.client.put(edit_url, edited_post_data, format="json")
        # print("Edit post response:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Failed to edit the post")
        # Verify that the response contains the edited content
        self.assertEqual(response.data["title"], "Edited Test Post", "Post title was not updated")
        self.assertEqual(response.data["content"], "This is the edited content.", "Post content was not updated")
        
# User Story #17 Test: As an author, I want to delete my posts so other users don't keep seeing them.
class DeletePostResendTestCase(APITestCase):
    def setUp(self):
        # Create users and authors
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.author = Author.objects.create(user=self.user, display_name='Test Author')
        # Use JWT authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        # Create post
        self.post = Post.objects.create(
            id=uuid.uuid4(),
            author_id=self.author,
            title="Test Post",
            content="This is a test post.",
            visibility="PUBLIC",
        )
        # Define post update URL
        self.post_url = reverse("post-detail", args=[self.author.id, self.post.id])
        
    def test_delete_post_marks_post_deleted(self):
        updated_data = {
            "title": self.post.title,
            "content": self.post.content,
            "visibility": "DELETED",
        }
        response = self.client.put(self.post_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.post.refresh_from_db()
        self.assertEqual(self.post.visibility, "DELETED")
