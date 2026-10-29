from urllib.parse import urlparse
from django.shortcuts import render
import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from .models import Author 
from .serializers import AuthorSerializer, AuthorEditProfileSerializer, LoginSerializer 
from django.shortcuts import get_object_or_404  
from rest_framework.views import APIView  
from rest_framework.generics import ListAPIView  
from rest_framework.permissions import IsAuthenticated, AllowAny  
from rest_framework_simplejwt.tokens import RefreshToken  
from rest_framework_simplejwt.authentication import JWTAuthentication  
from django.contrib.auth.models import User  
from django.db import transaction  
from rest_framework.reverse import reverse 
from .models import Author, Follows  
from django.utils import timezone  
from django.conf import settings  
import uuid  
from posts.models import Post  
from django.middleware.csrf import get_token  
from django.contrib.auth import authenticate  
from django.http import HttpRequest
from .pagination import AuthorsPagination  
from posts.serializers import PostSerializer  
from uuid import UUID 
from urllib.parse import urlparse
from rest_framework.exceptions import NotFound
from rest_framework.throttling import ScopedRateThrottle
import urllib.parse

from .utils import is_fqid, upload_to_imgur, is_request_author, get_request_author, are_friends, parse_uuid

# Default profile picture URL to be used when no image is provided
DEFAULT_PROFILE_PIC = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"

# Function to create an Author instance
def create_author(author_data, request, user):
    author_id = author_data.get('id', uuid.uuid4())  # Generate or get the UUID for the author
    host = request.build_absolute_uri('/')[:-1]  # Build the host
    #page_url = reverse('author-detail', kwargs={'pk': author_id}, request=request)  # Generate the URL for the author's page
    page_url = f"{host}/authors/{author_id}"
    author = Author.objects.create(  # Create the Author object
        id=author_id,
        host=host,
        display_name=author_data['displayName'],  # Set display name
        profile_image=author_data.get('profileImage', DEFAULT_PROFILE_PIC),  # Set the profile image or default one
        page=page_url,
        github=author_data.get('github', ''),  # Optional GitHub URL
        user=user  # Associate the Author with the created user
    )
    return author  # Return the newly created Author object

# View for handling login functionality
class LoginView(APIView):
    permission_classes = [AllowAny]  # No authentication required to access this view
    
    def post(self, request):
        # Deserialize and validate input data
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Invalid username or password"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve username and password from the validated data
        username = serializer.validated_data.get("username")
        password = serializer.validated_data.get("password")
        
        # Authenticate the user
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:  # Check if the user is active
            return Response({"error": "User account is not activated. Please contact an admin."}, status=status.HTTP_403_FORBIDDEN)
        
        author = Author.objects.filter(user=user).first()  # Fetch the associated Author
        if author is None:
            # e.g. an admin account made with createsuperuser, which has no author profile
            return Response({"error": "This account can only sign in to the admin panel."}, status=status.HTTP_403_FORBIDDEN)
        author_id = author.id
        refresh = RefreshToken.for_user(user)  # Generate JWT refresh token for the user
        access_token = str(refresh.access_token)  # Get the access token from the refresh token
        
        # Return tokens and author_id in the response
        response = Response({
            "author_id": author_id,
            "refresh_token": str(refresh),
            "access_token": access_token
        }, status=status.HTTP_200_OK)

        # Set tokens in cookies for client-side usage (set to secure=False in this case)
        response.set_cookie(
            'author_id', 
            author_id, 
            httponly=True, 
            secure=False,  # Should be True in production when using HTTPS
            samesite='None',
            path='/'
        )
        response.set_cookie(
            'access_token', 
            access_token, 
            httponly=True, 
            secure=False, 
            samesite='None',
            path='/'
        )
        response.set_cookie(
            'refresh_token', 
            str(refresh), 
            httponly=True, 
            secure=False, 
            samesite='None',
            path='/'
        )

        return response  # Return the final response containing the tokens

# Signup view for user registration
class SignUpView(APIView):
    http_method_names = ["post"]  # Only POST requests allowed
    permission_classes = [AllowAny]  # No authentication required for signup

    def post(self, request):
        # Get required data from the request body
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        display_name = request.data.get("displayName")
        github = request.data.get("github", "")
        profile_image = request.data.get("profileImage", DEFAULT_PROFILE_PIC)

        # Validate that required fields are present
        if not all([username, email, password, display_name]):
            return Response(
                {"message": "Username, email, password, and displayName are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            return Response(
                {"message": "Username already exists."},
                status=status.HTTP_409_CONFLICT
            )
        
        try:
            # Use a transaction to ensure both user and author are created or rolled back if any issue occurs
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    # Accounts are active immediately; set SIGNUP_REQUIRES_APPROVAL=True to require admin approval
                    is_active=not settings.SIGNUP_REQUIRES_APPROVAL
                )
                user.date_joined = timezone.now()  # Set account creation time
                user.save()  # Save the User object
                
                # Create the corresponding Author object
                author_data = {
                    "displayName": display_name,
                    "profileImage": profile_image,
                    "github": github,
                }
                author = create_author(author_data, request, user)  # Call create_author to create the author
                
                # Serialize the author data to return it in the response
                serializer = AuthorSerializer(author, context={"request": request})
                
                response = Response(serializer.data, status=status.HTTP_201_CREATED)  # Return the serialized author
                return response
        except Exception as e:
            return Response(
                {"message": f"An error occurred: {str(e)}"},  # Handle any errors that occur
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# View for verifying if a JWT token is still valid
class VerifyTokenView(APIView):
    authentication_classes = [JWTAuthentication]  # Use JWT for authentication
    permission_classes = [IsAuthenticated]  # User must be authenticated

    def get(self, request):
        try:
            # Get the Author object associated with the user
            author = Author.objects.get(user=request.user)
            return Response({'authorId': str(author.id)}, status=200)  # Return the author's ID if found
        except Author.DoesNotExist:  # Return error if the author does not exist
            return Response({'error': 'Author not found'}, status=404)

# View to retrieve a specific author's details using the author ID (primary key)
class AuthorDetailView(generics.RetrieveAPIView):
    queryset = Author.objects.all()  # Base queryset
    serializer_class = AuthorSerializer

    def get_object(self):
        """
        Override get_object to handle both SERIALs (local IDs) and FQIDs (URLs).
        """
        pk = self.kwargs.get(self.lookup_field)  # Retrieve the 'pk' from the URL
        pk = str(pk)  # Convert the pk to a string

        # Check if `pk` is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            # Try to find the author by its URL (FQID)
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            # Try to find the author by its SERIAL (id)
            author = get_object_or_404(Author, id=pk)

        return author
# class AuthorDetailView(generics.RetrieveAPIView):
#     queryset = Author.objects.all()  # Specify the queryset of authors
#     serializer_class = AuthorSerializer  # Use the AuthorSerializer for serialization
#     lookup_field = 'pk'  # The lookup field used for retrieving a specific author is the primary key

class AuthorProfileView(APIView):
    def get_friends_count(self, request, pk):
        """Retrieve the count of mutual friends using FriendsView."""
        pk = str(pk)
        # check if pk is a URL (FQID) or a uuid (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
        pk = parse_uuid(pk)
        
        friends_view = FriendsView()
        friends_response = friends_view.get(request, pk=pk)
        return len(friends_response.data.get('friends', []))

    def get_follower_count(self, author):
        """Retrieve the count of followers with accepted follow requests."""
        return Follows.objects.filter(followed_id=author, status='ACCEPTED').count()

    def get_following_count(self, author):
        """Retrieve the count of authors that the user is following with accepted follow requests."""
        return Follows.objects.filter(local_follower_id=author, status='ACCEPTED').count()

    def get_author_posts(self, author, visibility):
        """Retrieve posts by visibility and serialize them."""
        return PostSerializer(
            Post.objects.filter(author_id=author, visibility=visibility).order_by('-published'), many=True
        ).data

    def get(self, request, pk):
        pk = str(pk)
        # Retrieve the author instance by primary key (pk)
        # check if pk is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            author = get_object_or_404(Author, pk=pk)
        
        # Serialize author data
        author_data = AuthorSerializer(author).data
        
        # Gather counts and categorized posts
        friends_count = self.get_friends_count(request, pk=author.id)
        followers_count = self.get_follower_count(author)
        following_count = self.get_following_count(author)
        public_posts = self.get_author_posts(author, 'PUBLIC')
        # friends-only posts are shown to the author and their friends only
        viewer = get_request_author(request)
        can_see_friends_posts = viewer is not None and (viewer.id == author.id or are_friends(viewer, author))
        friends_posts = self.get_author_posts(author, 'FRIENDS') if can_see_friends_posts else []
        unlisted_posts = self.get_author_posts(author, 'UNLISTED')
        shared_posts = self.get_author_posts(author, 'SHARED')
        
        # Prepare the response data
        data = {
            **author_data,
            'friends_count': friends_count,
            'followers_count': followers_count,
            'following_count': following_count,
            'public_posts': public_posts,
            'friends_posts': friends_posts,
            'unlisted_posts': unlisted_posts,
            'shared_posts': shared_posts,
        }
        
        return Response(data)

class AuthorEditProfileView(APIView):
    def get(self, request, pk):
        pk = str(pk)
        # Retrieve the author by primary key (pk)
        # check if pk is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            author = get_object_or_404(Author, pk=pk)
        
        # Serialize the author for editing profile purposes
        serializer = AuthorEditProfileSerializer(author)
        
        # Return the serialized data
        return Response(serializer.data)

    def put(self, request, pk):
        pk = str(pk)
        # Retrieve the author instance by primary key (pk)
        # check if pk is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            author = get_object_or_404(Author, pk=pk)
        
        if not is_request_author(request, author.id):
            return Response({"error": "You can only edit your own profile."}, status=status.HTTP_403_FORBIDDEN)

        # Deserialize and validate the incoming data
        serializer = AuthorEditProfileSerializer(author, data=request.data)
        if serializer.is_valid():
            # Save the validated data
            serializer.save()
            return Response(serializer.data)
        
        # Return validation errors if the data is not valid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthorsView(ListAPIView): #used ListAPIView because this is used to handle a collection of model instances AND comes with pagination
    authentication_classes = [JWTAuthentication]
    #asked chatGPT how to get the authors using ListAPIView 2024-10-18
    # variables that ListAPIView needs
    serializer_class = AuthorSerializer
    pagination_class = AuthorsPagination
    
    def get_queryset(self):
        return Author.objects.all().order_by('created_at')
    
    def get(self, request, *args, **kwargs): #args and kwargs for the page and size 
        #retrieve all profiles on the node (paginated)
        response = super().get(request, *args, **kwargs) #get provided by ListAPIView that queries database, serializes, and handles pagination

        #customize structure of response
        response.data = {
        "type": "authors",  
        "authors": response.data['results']  
        }

        return response
    
class GetAllAuthorsView(APIView): 
    # unpaginated list of every author, used by the frontend search bar
    def get(self, request): 
        all_authors = Author.objects.all()
        serializer = AuthorSerializer(all_authors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class FollowerView(APIView):
    
    def get(self, request, author_id, follower_id):
        """
        Check if follower_id is a follower of author_id
        return 200 if following (accepted)
        return 202 if follow request pending (202 to indicate request is still in progress)
        return 404 if not following or requested
        """
        author = get_object_or_404(Author, id=author_id)

        # Check if the follow request has been accepted
        is_accepted = Follows.objects.filter(
            local_follower_id=follower_id, followed_id=author, status='ACCEPTED'
        ).exists()

        # Check if there's a pending follow request
        is_pending = Follows.objects.filter(
            local_follower_id=follower_id, followed_id=author, status='PENDING'
        ).exists()

        # Return appropriate response based on follower status
        if is_accepted:
            return Response({"status": "Following"}, status=status.HTTP_200_OK)

        if is_pending:
            return Response({"status": "Follow request pending"}, status=status.HTTP_202_ACCEPTED)

        # TODO: Update documentation!
        # Return 404 if follower not found or follow request doesn't exist
        return Response({"status": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, author_id, follower_id):        
        # only the author being followed can accept a request
        if not is_request_author(request, author_id):
            return Response({"error": "You can only accept your own follow requests."}, status=status.HTTP_403_FORBIDDEN)

        # get follow_request
        follow_request = Follows.objects.filter(followed_id=author_id, local_follower_id=follower_id).first()
        
        if not follow_request:
            return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # update status to "ACCEPTED"
        follow_request.status = 'ACCEPTED'
        follow_request.save()
        
        return Response({"status": "Follow request accepted"}, status=status.HTTP_200_OK)



    def delete(self, request, author_id, follower_id):
        # the followed author can deny/remove a follower, and the follower can unfollow
        if not is_request_author(request, author_id, follower_id):
            return Response({"error": "You can only remove follows you are part of."}, status=status.HTTP_403_FORBIDDEN)
        
        # get follow_request
        follow_request = Follows.objects.filter(followed_id=author_id, local_follower_id=follower_id).first()

        if not follow_request:
            return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

        
        # delete follow_request
        follow_request.delete()

        return Response({"status": "Follow request denied"}, status=status.HTTP_204_NO_CONTENT)




class UnfollowView(APIView):
    def delete(self, request, author_id, follower_id):
        try:
            # Validate UUID format
            author_id = UUID(author_id)
            follower_id = UUID(follower_id)
        except ValueError:
            return Response({'error': 'Invalid author or follower ID format.'}, status=400)

        if not is_request_author(request, author_id, follower_id):
            return Response({'error': 'You can only remove follows you are part of.'}, status=403)
        
        try:
            # find corresponding follow relationship
            follow = Follows.objects.get(followed_id=author_id, local_follower_id=follower_id)
            
            # delete follow relationship
            follow.delete()
            return Response({'message': 'Successfully unfollowed the author.'}, status=200)
        
        except Follows.DoesNotExist:
            return Response({'error': 'Follow relationship does not exist.'}, status=404)

class FollowersDetailView(APIView):
    def get(self, request, pk):  # Add 'pk' parameter
        pk = str(pk)
        # Get the author based on the provided pk
        # check if pk is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            author = get_object_or_404(Author, id=pk)
        
        # Retrieve all followers who have an accepted follow request for the author
        followers = Follows.objects.filter(followed_id=author, status='ACCEPTED').select_related('local_follower_id')
        
        followers_data = [
            {
                "type": "author",
                "id": request.build_absolute_uri(f'/authors/{follower.local_follower_id.id}/'),  # Full URL for ID 
                "host": request.build_absolute_uri('/'),  # Builds the host URL dynamically
                "displayName": follower.local_follower_id.display_name, 
                "page": request.build_absolute_uri(f'/authors/{follower.local_follower_id.id}/'),
                "github": follower.local_follower_id.github,  # Assuming github is a field on the Author model
                "profileImage": follower.local_follower_id.profile_image if follower.local_follower_id.profile_image else None
            } 
            for follower in followers
        ]

        # Return the list of followers with HTTP 200 status
        return Response({
            "type": "followers",
            "followers": followers_data
        }, status=status.HTTP_200_OK)

class FollowingDetailView(APIView):
    def get(self, request, pk):  # Add 'pk' parameter for the current user's ID
        pk = str(pk)
        # Get the author based on the provided pk (the current user)
        # check if pk is a URL (FQID) or an integer (SERIAL)
        if is_fqid(pk):
            pk = urllib.parse.unquote(pk)
            # if no trailing slash, append it
            if not pk.endswith('/'):
                pk += '/'
            author = get_object_or_404(Author, url=pk)
        else:
            pk = parse_uuid(pk)
            author = get_object_or_404(Author, id=pk)
            
        
        # Retrieve all users that the author is following with accepted follow requests
        following = Follows.objects.filter(local_follower_id=author, status='ACCEPTED').select_related('followed_id')
        
        # Create a list of following users' details with additional fields
        following_data = [
            {
                "type": "author",
                "id": request.build_absolute_uri(f'/authors/{follow.followed_id.id}/'),  # Full URL for ID
                "host": request.build_absolute_uri('/'),  # Builds the host URL dynamically
                "displayName": follow.followed_id.display_name,
                "page": request.build_absolute_uri(f'/authors/{follow.followed_id.id}/'),
                "github": follow.followed_id.github,  # Assuming github is a field on the Author model
                "profileImage": follow.followed_id.profile_image if follow.followed_id.profile_image else None
            }
            for follow in following
        ]

        # Return the list of following users with HTTP 200 status
        return Response({
            "type": "following",
            "following": following_data
        }, status=status.HTTP_200_OK)

class FriendsView(APIView):

    def get(self, request, pk=None):
        # Get the current logged-in user (Author instance)
        current_user = get_object_or_404(Author, user=request.user)

        # Check if an author_id is provided, else use the current logged-in user as the viewed author
        if pk:
            pk = str(pk)
            # check if pk is a URL (FQID) or an integer (SERIAL)
            if is_fqid(pk):
                pk = urllib.parse.unquote(pk)
                # if no trailing slash, append it
                if not pk.endswith('/'):
                    pk += '/'
                viewed_author = get_object_or_404(Author, url=pk)
            else:
                pk = parse_uuid(pk)
                viewed_author = get_object_or_404(Author, id=pk)
        else:
            viewed_author = current_user

        # Get all authors that the viewed author is following and the follow status is ACCEPTED
        following_ids = Follows.objects.filter(local_follower_id=viewed_author, status='ACCEPTED').values_list('followed_id', flat=True)
        
        # Get all authors who follow the viewed author and the follow status is ACCEPTED
        followers_ids = Follows.objects.filter(followed_id=viewed_author, status='ACCEPTED').values_list('local_follower_id', flat=True)

        # Find mutual friends by intersecting the sets of followers and followings
        mutual_friend_ids = set(following_ids).intersection(set(followers_ids))

        # Retrieve all mutual friends (Authors)
        friends = Author.objects.filter(id__in=mutual_friend_ids)

        # Create a list of friends' details with additional fields
        friends_data = [
            {
                "type": "author",
                "id": request.build_absolute_uri(f'/authors/{friend.id}/'),  # Full URL for ID
                "host": request.build_absolute_uri('/'),  # Builds the host URL dynamically
                "displayName": friend.display_name,
                "page": request.build_absolute_uri(f'/authors/{friend.id}/'),
                "github": friend.github,  # Assuming github is a field on the Author model
                "profileImage": friend.profile_image if friend.profile_image else None
            }
            for friend in friends
        ]

        # Return the list of friends with HTTP 200 status
        return Response({
            "type": "friends",
            "friends": friends_data
        }, status=status.HTTP_200_OK)
    
# Largest profile picture accepted by ProfileImageUploadView
MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024

class ProfileImageUploadView(APIView):
    permission_classes = [AllowAny]  # Signup uploads the picture before the account exists
    # Limit uploads per client so the endpoint can't be used as free image hosting
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'image_upload'

    def post(self, request, username):
        try:
            # Ensure the username is provided
            if not username:
                return Response({"error": "ProfileImageUploadView - POST - Username is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if a file (profile image) was uploaded in the request
            file = request.FILES.get('profile_image')
            if not file:
                return Response({"error": "ProfileImageUploadView - POST - No image file was provided."}, status=status.HTTP_400_BAD_REQUEST)

            if not (file.content_type or '').startswith('image/'):
                return Response({"error": "Profile picture must be an image file."}, status=status.HTTP_400_BAD_REQUEST)

            if file.size > MAX_PROFILE_IMAGE_BYTES:
                return Response({"error": "Profile picture must be 5 MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

            imgur_url, error = upload_to_imgur(file)
            if error:
                return Response({"error": f"ProfileImageUploadView - POST - Couldn't upload {file.name}: {str(error)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({"message": "Profile image uploaded successfully.", "url": imgur_url[0]}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"ProfileImageUploadView - POST - Error: {str(e)}")
            return Response({"error": f"ProfileImageUploadView - POST - {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        #     # Create a unique file path for saving the image based on the username
        #     file_path = f'profiles/{username}/{file.name}'
        #     full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        #     # Ensure the directory exists (create if necessary)
        #     os.makedirs(os.path.dirname(full_path), exist_ok=True)

        #     # Save the file to the media folder in chunks
        #     with open(full_path, 'wb+') as destination:
        #         for chunk in file.chunks():
        #             destination.write(chunk)

        #     # Construct the media URL for accessing the profile image via HTTP
        #     base_url = self.get_base_url(request)
        #     media_url = f'{base_url}{settings.MEDIA_URL}{file_path}'

        #     # Return a success message along with the image URL
        #     return Response({"message": "Profile image uploaded successfully", "url": media_url}, status=status.HTTP_200_OK)
        
        # except Exception as e:
        #     # Handle any errors and return a server error response
        #     return Response({"error": f"Failed to upload profile image: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def get_base_url(self, request: HttpRequest):
    #     """
    #     Generate the base URL (protocol + host) based on the request.
    #     """
    #     protocol = 'https' if request.is_secure() else 'http'
    #     host = request.get_host()  # This gives the hostname and port (if not default)
    #     return f'{protocol}://{host}'