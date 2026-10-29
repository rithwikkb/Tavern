from django.urls import path
from .views import (
    FollowerView, 
    AuthorsView,
    UnfollowView,
    FollowersDetailView,
    FriendsView,
)

"""
for user urls that start with api/authors/
"""
urlpatterns = [
    path('', AuthorsView.as_view(), name='authors-list'),
    path('<str:author_id>/followers/<str:follower_id>/', FollowerView.as_view(), name='manage_follow_request'), #Manage Follow Request
    path('<str:author_id>/followers/<str:follower_id>/unfollow/', UnfollowView.as_view(), name='unfollow'),
    path('<str:pk>/followers/', FollowersDetailView.as_view(), name='followers'),
    path('<str:pk>/friends/', FriendsView.as_view(), name='friends'),
]