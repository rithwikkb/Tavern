from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Author, Follows
from rest_framework.test import APITestCase
from stream.models import Inbox  
import uuid
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Author, Follows
from posts.models import Post

class LoginViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name='Test User')
        self.url = reverse('login')  

    def test_login_success(self):
        data = {"username": "testuser", "password": "testpass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertFalse(response.data['is_demo'])

    def test_login_invalid_credentials(self):
        data = {"username": "wronguser", "password": "wrongpass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        
class SignUpViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('signup')  

    def test_signup_success(self):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Tavern-strong-pass-42",
            "displayName": "New User",
            "github": "https://github.com/newuser"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['displayName'], 'New User')

    def test_signup_rejects_weak_password(self):
        data = {
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "password",
            "displayName": "Weak User",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("too common", response.data["message"])
        self.assertFalse(User.objects.filter(username="weakuser").exists())

    def test_signup_username_exists(self):
        User.objects.create_user(username='newuser', password='testpass')
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Tavern-strong-pass-42",
            "displayName": "New User"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('message', response.data)

    def test_signup_missing_fields(self):
        data = {
            "username": "newuser",
            "password": "Tavern-strong-pass-42",
            "displayName": "New User"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)


class LogoutViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.url = reverse('logout')

    def test_logout_success(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
class VerifyTokenViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name='Test User')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.url = reverse('verify-token')  
    def test_verify_token_valid(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['authorId'], str(self.author.id))

    def test_verify_token_invalid(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalidtoken')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
class AuthorDetailViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name='Test User')
        self.url = reverse('author-detail', kwargs={'pk': self.author.id})
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_author_detail(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['displayName'], 'Test User')
    def test_author_detail_not_found(self):
        non_existing_uuid = uuid.uuid4()
        response = self.client.get(reverse('author-detail', kwargs={'pk': non_existing_uuid}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

# User Story #4 Test: As an author, I want a public page with my profile information.
class AuthorProfileViewTest(APITestCase):
    def setUp(self):
        # Creating a user and associated author
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name='Test Author', github='https://github.com/testauthor')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Creating posts with various visibility statuses
        Post.objects.create(
            author_id=self.author,
            title="Public Post",
            content="This is a public post.",
            content_type='text/plain',
            visibility='PUBLIC'
        )
        Post.objects.create(
            author_id=self.author,
            title="Friends Post",
            content="This is a friends-only post.",
            content_type='text/plain',
            visibility='FRIENDS'
        )
        Post.objects.create(
            author_id=self.author,
            title="Unlisted Post",
            content="This is an unlisted post.",
            content_type='text/plain',
            visibility='UNLISTED'
        )
        
        # Creating a follower relationship
        self.follower = Author.objects.create(display_name="Follower Author", github="https://github.com/followerauthor")
        Follows.objects.create(local_follower_id=self.follower, followed_id=self.author, status='ACCEPTED')

        # Defining the URL for the author profile
        self.url = reverse('author-profile', kwargs={'pk': str(self.author.id)})

    def test_author_profile_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['displayName'], 'Test Author')
        self.assertEqual(response.data['followers_count'], 1)
        # posts come from the paged timeline, not the profile itself
        self.assertNotIn('public_posts', response.data)
        timeline = self.client.get(f'/api/authors/{self.author.id}/timeline/').data
        self.assertEqual({p['title'] for p in timeline['posts']}, {'Public Post', 'Friends Post', 'Unlisted Post'})

    def test_author_profile_not_found(self):
        non_existing_uuid = uuid.uuid4()
        url = reverse('author-profile', kwargs={'pk': non_existing_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AuthorEditProfileViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name="Test Author", github="https://github.com/testauthor")
        
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.url = reverse('author-edit-profile', kwargs={'pk': str(self.author.id)})

    def test_get_author_profile_for_editing(self):
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Test Author')

    def test_edit_author_profile_success(self):
        data = {
            "display_name": "Updated Test Author",
            "github": "https://github.com/updatedauthor"
        }
        
        response = self.client.put(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Test Author')

    def test_edit_author_profile_invalid_data(self):
        data = {
            "display_name": "",  
        }
        
        
        response = self.client.put(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('display_name', response.data)

class AuthorsViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(user=self.user, display_name="Authenticated Author")

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.author1 = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author 1",
            github="https://github.com/author1"
        )
        self.author2 = Author.objects.create(
            id=uuid.uuid4(),
            display_name="Author 2",
            github="https://github.com/author2"
        )

        self.url = reverse('authors-list')

    def test_empty_authors_list(self):
        Author.objects.all().delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['authors'], [])

class FollowRequestTestCase(TestCase):
    def setUp(self):
        # Create two authors for testing purposes
        self.author1 = Author.objects.create(
            id=uuid.uuid4(),
            host='http://example.com/',
            display_name='Author 1',
            github='http://github.com/author1',
            profile_image='http://example.com/author1/image'
        )
        self.author2 = Author.objects.create(
            id=uuid.uuid4(),
            host='http://example.com/',
            display_name='Author 2',
            github='http://github.com/author2',
            profile_image='http://example.com/author2/image'
        )

        # Create test user; they are author2, who receives the follow request
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.author2.user = self.user
        self.author2.save()

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Initialize API client
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)  # Use JWT authentication

        # Create Follows request
        self.follow_request = Follows.objects.create(
            local_follower_id=self.author1,
            followed_id=self.author2,
            status='PENDING'
        )

        # Create Inbox entry
        content_type = ContentType.objects.get_for_model(Follows)
        self.inbox_entry = Inbox.objects.create(
            author=self.author2,
            content_type=content_type,
            object_id=self.follow_request.id,
            content_object=self.follow_request
        )

        # Set the URL with author1.id as follower_id
        self.url = reverse('manage_follow_request', kwargs={
            'author_id': str(self.author2.id),  
            'follower_id': str(self.author1.id)  # Use author1 as the follower
        })
        
        # print(f"Generated URL: {self.url}")

    def test_approve_follow_request(self):
        # Send a PUT request to approve the follow request
        response = self.client.put(self.url, format='json')

        # Confirm that the status code is 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_deny_follow_request(self):
        # Send a DELETE request to deny the follow request
        response = self.client.delete(self.url)

        # Confirm that the status code is 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify that the follow_request has been deleted
        self.assertFalse(Follows.objects.filter(id=self.follow_request.id).exists())

class UnfollowTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Initialize API client
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)  # Use JWT authentication

        # Create test authors and follow relationship
        self.author1 = Author.objects.create(
            id=uuid.uuid4(), 
            display_name='Author 1', 
            host='http://localhost/', 
            page='http://localhost/author1',
            user=self.user  # Associate the created user with Author
        )
        self.author2 = Author.objects.create(
            id=uuid.uuid4(), 
            display_name='Author 2', 
            host='http://localhost/', 
            page='http://localhost/author2'
        )
        
        self.follow = Follows.objects.create(
            local_follower_id=self.author1, 
            followed_id=self.author2,
            status='ACCEPTED'
        )

        self.unfollow_url = reverse('unfollow', kwargs={
            'author_id': str(self.author2.id),
            'follower_id': str(self.author1.id)
        })

    def test_unfollow_success(self):
        # Test successful unfollow
        response = self.client.delete(self.unfollow_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Successfully unfollowed the author.')

        # Ensure the follow relationship is deleted from the database
        follow_exists = Follows.objects.filter(
            followed_id=self.author2, 
            local_follower_id=self.author1
        ).exists()
        self.assertFalse(follow_exists)


# User Story #2 Test: As an author, I want a consistent identity per node.
class AuthorUrlTestCase(APITestCase):
    def setUp(self):
        # Create test users and authors
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.author = Author.objects.create(
            user=self.user,
            display_name="Test User",
            host="http://example.com",
            github="https://github.com/testuser"
        )

        # API URL for author detail
        self.url = reverse('author-detail', kwargs={'pk': self.author.id})

        # Set up authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_author_url_generation(self):
        # Verify that the URL is generated correctly
        expected_url = f"http://example.com/api/authors/{self.author.id}/"
        self.assertEqual(self.author.url, expected_url)
    
    def test_author_url_consistency(self):
        # Modify other fields and verify that the URL is consistent
        original_url = self.author.url
        self.author.display_name = "Updated Author"
        self.author.save()
        self.assertEqual(self.author.url, original_url)
        
    def test_author_url_in_api_response(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Adjusted to allow both with and without trailing slash
        expected_url = f"http://example.com/api/authors/{self.author.id}/"
        actual_url = response.data['id']
        self.assertTrue(
            actual_url == expected_url or actual_url == expected_url.rstrip('/'),
            f"URL mismatch: Expected {expected_url}, got {actual_url}"
        )
    
    def test_author_detail_not_found(self):
        # Test for non-existent author
        non_existing_uuid = uuid.uuid4()
        response = self.client.get(reverse('author-detail', kwargs={'pk': non_existing_uuid}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

# User Story #2 Test: As an author, I want a consistent identity per node.
class AuthorApiConsistencyTestCase(APITestCase):
    def setUp(self):
        # Create test users and multiple authors
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.authors = [
            Author.objects.create(
                id=uuid.uuid4(),
                host="http://example.com",
                display_name=f"Author {i}",
                github=f"http://github.com/author{i}"
            ) for i in range(3)
        ]

        # Set up authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
    def test_multiple_authors_url_uniqueness(self):
        # Verify URL uniqueness
        urls = [f"http://example.com/api/authors/{author.id}/" for author in self.authors]
        self.assertEqual(len(urls), len(set(urls)))  
        for author in self.authors:
            expected_url = f"http://example.com/api/authors/{author.id}/"
            self.assertEqual(f"http://example.com/api/authors/{author.id}/", expected_url)

    def test_deleted_authors_not_in_api_list(self):
        # After removing an author, verify that it no longer appears in the API list
        deleted_author = self.authors[0]
        deleted_author.delete()
        response = self.client.get("/api/authors/")
        self.assertEqual(response.status_code, 200)
        # Check if the `id` field does not contain a deleted author
        self.assertNotIn(
            str(deleted_author.id), 
            [author["id"] for author in response.json()["authors"]]
        )

    def test_api_author_list_url_format(self):
        # Verify that the `id` format in the author list is correct
        response = self.client.get("/api/authors/")
        self.assertEqual(response.status_code, 200)
        for author in response.json()["authors"]:
            self.assertTrue(
                author["id"].startswith("http://example.com/api/authors/")  
            )

# User Story #3 Test: As a node admin, I want to host multiple authors on my node, so I can have a friendly online community.
class AdminManagementTests(APITestCase):
    def setUp(self):
        # Create an admin user
        self.admin_user = User.objects.create_superuser(username="admin", password="password123")
        Author.objects.create(
            user=self.admin_user,
            display_name="Admin Author",
            github="https://github.com/admin"
        )

        # Create multiple users and their associated authors
        for i in range(15):
            user = User.objects.create_user(username=f"user{i}", password="password123")
            Author.objects.create(
                user=user,
                display_name=f"Author{i}",
                github=f"https://github.com/user{i}"
            )

        # Log in as administrator user and obtain JWT Token
        response = self.client.post('/api/login/', {
            'username': 'admin',
            'password': 'password123'
        })
        # print(f"Login Response: {response.status_code}, {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Unexpected response: {response.data}")

        # Dynamically extract access token
        access_token = response.data.get('access_token')
        self.assertIsNotNone(access_token, "Access token not found in response")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    def test_get_all_authors(self):
        # Test to get a list of all authors
        response = self.client.get("/api/authors/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "authors")
        self.assertTrue("authors" in response.data)
        self.assertTrue(len(response.data["authors"]) <= 10)  # Assuming pagination returns a maximum of 10 authors per page
    
    def test_author_not_found(self):
        # Test to get non-existent author
        response = self.client.get("/api/authors/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No Author matches the given query.")


class AdminAccountLoginTest(TestCase):
    def test_admin_without_author_profile_gets_clear_error(self):
        User.objects.create_superuser(username="admin", email="admin@example.com", password="Admin-pass-123")
        response = self.client.post(
            "/api/login/",
            {"username": "admin", "password": "Admin-pass-123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("admin panel", response.json()["error"])


class ProfileLinkValidationTest(TestCase):
    """GitHub links and profile images are rendered as links/images, so only http(s) URLs are allowed."""
    def test_signup_rejects_javascript_github_link(self):
        response = self.client.post("/api/signup/", {
            "username": "linky", "email": "l@example.com", "password": "Tavern-strong-pass-42",
            "displayName": "Linky", "github": "javascript:alert(document.cookie)",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="linky").exists())

    def test_signup_rejects_oversized_profile_image(self):
        response = self.client.post("/api/signup/", {
            "username": "bigpic", "email": "b@example.com", "password": "Tavern-strong-pass-42",
            "displayName": "Big", "profileImage": "A" * 100_000,
        }, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_profile_edit_rejects_non_url_image(self):
        user = User.objects.create_user(username="editor", password="Tavern-strong-pass-42")
        author = Author.objects.create(display_name="Editor", host="http://testserver", user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + str(RefreshToken.for_user(user).access_token))
        response = client.put(f"/api/authors/{author.id}/profile/edit/", {
            "display_name": "Editor", "profile_image": "javascript:alert(1)",
        }, format="json")
        self.assertEqual(response.status_code, 400)


class SeedDemoTest(TestCase):
    """seed_demo builds the demo community, can be re-run safely, and the demo account is protected."""
    def seed(self):
        from django.core.management import call_command
        from io import StringIO
        call_command("seed_demo", "--site-url", "http://testserver", stdout=StringIO())

    def test_seed_is_idempotent(self):
        from posts.models import Post, Comment, Like
        self.seed()
        counts = (User.objects.count(), Author.objects.count(), Post.objects.count(),
                  Comment.objects.count(), Like.objects.count(), Follows.objects.count())
        self.seed()
        self.assertEqual(counts, (User.objects.count(), Author.objects.count(), Post.objects.count(),
                                  Comment.objects.count(), Like.objects.count(), Follows.objects.count()))
        self.assertGreater(counts[2], 5)

    def test_demo_login_sees_populated_feed(self):
        from django.conf import settings
        self.seed()
        client = APIClient()
        login = client.post("/api/login/", {"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["is_demo"])
        client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access_token"])
        posts = client.get("/api/posts/").data["posts"]
        visibilities = {p["visibility"] for p in posts}
        # friends-only (from Avery) and unlisted (from Jordan, whom demo follows) are visible to demo
        self.assertTrue({"PUBLIC", "FRIENDS", "UNLISTED"} <= visibilities, visibilities)
        requests = client.get(f"/api/authors/{login.data['author_id']}/inbox/follow_requests/")
        self.assertEqual(len(requests.data), 1)

    def test_sample_people_cannot_log_in(self):
        self.seed()
        self.assertFalse(User.objects.get(username="sample_avery").has_usable_password())

    def test_demo_profile_cannot_be_edited(self):
        from django.conf import settings
        self.seed()
        client = APIClient()
        login = client.post("/api/login/", {"username": settings.DEMO_USERNAME, "password": settings.DEMO_PASSWORD}, format="json")
        client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access_token"])
        response = client.put(f"/api/authors/{login.data['author_id']}/profile/edit/", {"display_name": "Renamed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Author.objects.get(id=login.data["author_id"]).display_name, "Demo Visitor")

    def test_reserved_usernames_cannot_sign_up(self):
        for username in ["demo", "sample_avery", "Sample_Someone"]:
            response = self.client.post("/api/signup/", {
                "username": username, "email": "r@example.com", "password": "Tavern-strong-pass-42", "displayName": "R",
            }, content_type="application/json")
            self.assertEqual(response.status_code, 409, username)

    def test_seed_refuses_to_take_over_real_account(self):
        from django.core.management.base import CommandError
        User.objects.create_user(username="sample_avery", password="Someones-real-pass-1")
        with self.assertRaises(CommandError):
            self.seed()


class StaleTokenLoginTest(TestCase):
    """An expired/invalid token left in the browser must not stop someone logging in or signing up."""
    def test_login_and_signup_ignore_invalid_token(self):
        user = User.objects.create_user(username="returning", password="Tavern-strong-pass-42")
        Author.objects.create(display_name="Returning", host="http://testserver", user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not.a.valid.token")

        response = client.post("/api/login/", {"username": "returning", "password": "Tavern-strong-pass-42"}, format="json")
        self.assertEqual(response.status_code, 200)

        response = client.post("/api/signup/", {
            "username": "newcomer", "email": "n@example.com", "password": "Tavern-strong-pass-42", "displayName": "N",
        }, format="json")
        self.assertEqual(response.status_code, 201)


class DemoResetTest(TestCase):
    """Logging in as the demo undoes earlier visitors' changes, at most once per interval."""
    def setUp(self):
        from django.core.management import call_command
        from io import StringIO
        from django.conf import settings
        call_command("seed_demo", "--site-url", "http://testserver", stdout=StringIO())
        self.settings_ = settings
        self.demo_author = Author.objects.get(user__username=settings.DEMO_USERNAME)

    def login_demo(self):
        client = APIClient()
        response = client.post("/api/login/", {
            "username": self.settings_.DEMO_USERNAME, "password": self.settings_.DEMO_PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access_token"])
        return client

    def make_visitor_mess(self, client):
        from posts.models import Post, Like
        demo_id = self.demo_author.id
        # a visitor's own post, an unliked seeded post, and an accepted follow request
        client.post(f"/api/authors/{demo_id}/posts/", {"title": "visitor", "content": "x", "contentType": "text/plain", "visibility": "PUBLIC"}, format="json")
        sunset = Post.objects.get(title="Sunset from the ridge")
        Like.objects.filter(author_id=self.demo_author, object_id=sunset.id).delete()
        sam = Author.objects.get(user__username="sample_sam")
        client.put(f"/api/authors/{demo_id}/followers/{sam.id}/")
        return sunset, sam

    def assert_clean(self, sunset, sam):
        from posts.models import Post, Like
        self.assertFalse(Post.objects.filter(title="visitor").exists())
        self.assertTrue(Like.objects.filter(author_id=self.demo_author, object_id=sunset.id).exists())
        self.assertEqual(Follows.objects.get(local_follower_id=sam, followed_id=self.demo_author).status, "PENDING")

    def test_login_resets_demo(self):
        from posts.models import Post
        client = self.login_demo()
        sunset, sam = self.make_visitor_mess(client)
        self.assertTrue(Post.objects.filter(title="visitor").exists())

        # pretend the last reset was long ago, as it would be for the next visitor
        User.objects.filter(username=self.settings_.DEMO_USERNAME).update(last_login=None)
        self.login_demo()
        self.assert_clean(sunset, sam)

    def test_reset_restores_others_comments_on_demo_posts(self):
        from posts.models import Post, Comment, Like
        welcome = Post.objects.get(title="Welcome to Tavern 👋")
        before = (welcome.comments.count(), Like.objects.filter(object_id=welcome.id).count())
        self.assertGreater(before[0], 0)

        client = self.login_demo()
        # a visitor deletes the sample people's comments on the demo's post, then the post
        # (deleting a post in the app only marks it DELETED)
        for comment in welcome.comments.exclude(author_id=self.demo_author):
            response = client.delete(f"/api/authors/{comment.author_id_id}/commented/{comment.id}/")
            self.assertEqual(response.status_code, 204)
        Post.objects.filter(id=welcome.id).update(visibility="DELETED")
        self.assertEqual(Comment.objects.filter(post_id=welcome.id).count(), 0)

        User.objects.filter(username=self.settings_.DEMO_USERNAME).update(last_login=None)
        self.login_demo()
        welcome = Post.objects.get(id=welcome.id)
        self.assertEqual(welcome.visibility, "PUBLIC")
        self.assertEqual((welcome.comments.count(), Like.objects.filter(object_id=welcome.id).count()), before)

    def test_demo_has_unread_notifications_again_after_reset(self):
        from notifications.models import Notification
        client = self.login_demo()
        data = client.get("/api/notifications/").data
        verbs = {n["verb"] for n in data["notifications"]}
        self.assertTrue({"comment", "like_post", "follow", "follow_request"} <= verbs, verbs)
        self.assertEqual(data["unread_count"], len(data["notifications"]))

        client.post("/api/notifications/read/")
        self.assertEqual(client.get("/api/notifications/unread_count/").data["unread_count"], 0)

        # a visitor dismisses one, and another has expired
        dismissed = data["notifications"][0]["id"]
        client.post("/api/notifications/dismiss/", {"ids": [dismissed]}, format="json")
        from django.utils import timezone
        from datetime import timedelta
        Notification.objects.filter(recipient=self.demo_author).exclude(id=dismissed).filter(
            id=data["notifications"][1]["id"]).update(created=timezone.now() - timedelta(days=40))
        self.assertEqual(len(client.get("/api/notifications/").data["notifications"]), len(data["notifications"]) - 2)

        User.objects.filter(username=self.settings_.DEMO_USERNAME).update(last_login=None)
        client = self.login_demo()
        after = client.get("/api/notifications/").data
        self.assertEqual(len(after["notifications"]), len(data["notifications"]))
        self.assertEqual(after["unread_count"], len(after["notifications"]))

    def test_no_reset_within_interval(self):
        from posts.models import Post
        client = self.login_demo()  # resets and starts the interval
        self.make_visitor_mess(client)
        self.login_demo()  # second visitor right away: leave the first visitor's work alone
        self.assertTrue(Post.objects.filter(title="visitor").exists())

    def test_reset_keeps_real_users_content(self):
        from posts.models import Post, Comment
        real = User.objects.create_user(username="realperson", password="Tavern-strong-pass-42")
        real_author = Author.objects.create(display_name="Real", host="http://testserver", user=real)
        welcome = Post.objects.get(title="Welcome to Tavern 👋")
        Comment.objects.create(author_id=real_author, post_id=welcome, comment="hello from a real user")
        Post.objects.create(author_id=real_author, title="real post", content="c", content_type="text/plain")

        User.objects.filter(username=self.settings_.DEMO_USERNAME).update(last_login=None)
        self.login_demo()
        self.assertTrue(Comment.objects.filter(comment="hello from a real user").exists())
        self.assertTrue(Post.objects.filter(title="real post").exists())


class LogoutAndCookiesTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="leaver", password="Tavern-strong-pass-42")
        Author.objects.create(display_name="Leaver", host="http://testserver", user=user)
        self.client_ = APIClient()

    def test_login_sets_no_server_cookies(self):
        response = self.client_.post("/api/login/", {"username": "leaver", "password": "Tavern-strong-pass-42"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.cookies), 0)

    def test_logout_revokes_refresh_token(self):
        tokens = self.client_.post("/api/login/", {"username": "leaver", "password": "Tavern-strong-pass-42"}, format="json").data
        refresh = tokens["refresh_token"]
        self.assertEqual(self.client_.post("/api/users/token/refresh/", {"refresh": refresh}, format="json").status_code, 200)

        # a fresh login so the token we revoke hasn't already been rotated
        tokens = self.client_.post("/api/login/", {"username": "leaver", "password": "Tavern-strong-pass-42"}, format="json").data
        response = self.client_.post("/api/users/logout/", {"refresh": tokens["refresh_token"]}, format="json")
        self.assertEqual(response.status_code, 200)
        reuse = self.client_.post("/api/users/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json")
        self.assertEqual(reuse.status_code, 401)

    def test_logout_with_bad_token_still_succeeds(self):
        response = self.client_.post("/api/users/logout/", {"refresh": "garbage"}, format="json")
        self.assertEqual(response.status_code, 200)

