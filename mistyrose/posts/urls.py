from django.urls import path
from .views import GitHubEventsView, PostDetailsByFqidView, CommentsByFQIDView, PublicPostsView, LikesViewByFQIDView
urlpatterns = [
    # Comment URLs
    path('<path:post_fqid>/comments/', CommentsByFQIDView.as_view(), name='get_comments_fqid'),
      
    # Like URLs
    path('<path:post_fqid>/likes/', LikesViewByFQIDView.as_view(), name='get_likes_fqid'),
    
    # Post URLs
    path('github/events/<str:username>/', GitHubEventsView.as_view(), name='github-events'),
    path('', PublicPostsView.as_view(), name='public-posts'),
    path('<path:post_fqid>', PostDetailsByFqidView.as_view(), name='post-detail-fqid'),
    
]
