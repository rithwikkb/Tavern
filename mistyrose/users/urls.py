from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    SignUpView,
    AuthorDetailView,
    LogoutView,
    AuthorProfileView,
    AuthorEditProfileView,
    VerifyTokenView,
    ProfileImageUploadView,
    FollowersDetailView,
    FriendsView,
    FollowingDetailView,
    GetAllAuthorsView
)

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='login'),  # Use JWT for login
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),  # Refresh JWT token endpoint
    path('verify/', VerifyTokenView.as_view(), name='verify-token'),  # Verify JWT token endpoint
    path('api/signup/', SignUpView.as_view(), name='signup'),  # User signup endpoint
    path('logout/', LogoutView.as_view(), name='logout'),  # User logout endpoint
    path('api/authors/all/', GetAllAuthorsView.as_view(), name='all-authors'),
   
    path('authors/<str:username>/upload_image/', ProfileImageUploadView.as_view(), name='upload-profile-image'),
   
    path('api/authors/<uuid:pk>/profile/edit/', AuthorEditProfileView.as_view(), name='author-edit-profile'),  # Edit author profile
    path('api/authors/<uuid:pk>/profile/', AuthorProfileView.as_view(), name='author-profile'),  # Author profile view
    path('api/authors/<uuid:pk>/followers/', FollowersDetailView.as_view(), name='author-followers'),  # Followers endpoint
    path('api/authors/<uuid:pk>/friends/', FriendsView.as_view(), name='author-friends'),  # Friends endpoint
    path('api/authors/<uuid:pk>/following/', FollowingDetailView.as_view(), name='author-following'),  # Friends endpoint
   
    path('api/authors/<path:pk>/profile/edit/', AuthorEditProfileView.as_view(), name='author-edit-profile-fqid'),  # Edit author profile
    path('api/authors/<path:pk>/profile/', AuthorProfileView.as_view(), name='author-profile-fqid'),  # Author profile view
    path('api/authors/<path:pk>/followers/', FollowersDetailView.as_view(), name='author-followers-fqid'),  # Followers endpoint
    path('api/authors/<path:pk>/friends/', FriendsView.as_view(), name='author-friends-fqid'),  # Friends endpoint
    path('api/authors/<path:pk>/following/', FollowingDetailView.as_view(), name='author-following-fqid'),  # Friends endpoint
    path('api/authors/<path:pk>/', AuthorDetailView.as_view(), name='author-detail'),  # Author detail view
    path('authors/<path:pk>/', AuthorDetailView.as_view(), name='author-detail-fqid'),  # Author detail view
]