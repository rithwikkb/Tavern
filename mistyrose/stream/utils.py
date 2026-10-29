from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from users.models import Author, Follows
from posts.models import Post, Comment, Like
from .serializers import FollowSerializer
from posts.serializers import PostSerializer, CommentSerializer, LikeSerializer

def handle_follow_request(request, author):
  # Retrieve actor and object data, and handle None case
  actor_data = request.data.get('actor')
  object_data = request.data.get('object')

  # Check if actor_data and object_data exist
  if actor_data is None or 'id' not in actor_data:
      return Response({"error": "'actor' or 'actor.id' is missing from the request"}, status=status.HTTP_400_BAD_REQUEST)

  if object_data is None or 'id' not in object_data:
      return Response({"error": "'object' or 'object.id' is missing from the request"}, status=status.HTTP_400_BAD_REQUEST)

  # Extract actor_id and object_id safely
  actor_id = actor_data['id'].rstrip('/').split('/')[-1].rstrip('/')
  object_id = object_data['id'].rstrip('/').split('/')[-1].rstrip('/')

  serializer = FollowSerializer(data=request.data)
  existing_follow = Follows.objects.filter(
      local_follower_id=actor_id,
      followed_id=author,
  ).first()

  if existing_follow:
      return Response(FollowSerializer(existing_follow).data, status=status.HTTP_200_OK)

  if serializer.is_valid():
      serializer.validated_data['local_follower_id']['id'] = actor_id
      serializer.validated_data['followed_id']['id'] = object_id
      serializer.save()
      return Response(serializer.data, status=status.HTTP_201_CREATED)
  return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def handle_post_inbox(request, post_author, author_id):
  # create post object type and user.
  author = get_object_or_404(Author, id=author_id) #author whose stream we want to add post to

  if request.data.get('visibility') == 'PUBLIC':
      # check if post's author in database, create author if not
      author_of_post = request.data["author"]["id"]
      author_of_post_id = author_of_post.rstrip('/').split("/authors/")[-1]

      author_data = request.data["author"]
      # get or create remote author who made the post
      post_author, created = Author.objects.get_or_create(
          id=author_of_post_id,
          defaults={
              "host": author_data['host'],
              "display_name": author_data['displayName'],
              "github": author_data.get('github', ''),
              "profile_image": author_data.get('profileImage', ''),
              "page": author_data['page'],
          }
      )

  elif request.data.get('visibility') == 'FRIENDS':
      #check if poster's author in database and actually friends (if friends, should already be in database)
      author_of_post = request.data["author"]["id"]
      author_of_post_id = author_of_post.rstrip('/').split("/authors/")[-1]

      try:
          post_author = Author.objects.get(id=author_of_post_id)

          #check that they are actually friends
          are_friends = (
            Follows.objects.filter(local_follower_id=author, followed_id=post_author, status='ACCEPTED').exists() and #do you follow the poster's author?
            Follows.objects.filter(local_follower_id=post_author, followed_id=author, status='ACCEPTED').exists() #does poster follow you?
          )

          if not are_friends:
            return Response({"error": "Author is not a friend"}, status=status.HTTP_403_FORBIDDEN)
          
      except Author.DoesNotExist:
          return Response({"error": "Author is not a friend"}, status=status.HTTP_404_NOT_FOUND)
      
  elif request.data.get('visibility') == 'UNLISTED':
      #check if poster's author in database and actually friends (if friends, should already be in database)
      author_of_post = request.data["author"]["id"]
      author_of_post_id = author_of_post.rstrip('/').split("/authors/")[-1]

      try:
          post_author = Author.objects.get(id=author_of_post_id)

          is_follower = Follows.objects.filter(
                local_follower_id=author, followed_id=post_author, status='ACCEPTED'
            ).exists()
          if not is_follower:
                return Response(
                    {"error": "Current author is not following the post's author"},
                    status=status.HTTP_403_FORBIDDEN
                )
          
      except Author.DoesNotExist:
          return Response({"error": "Post author does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
      


  # Extract post ID from the data
  post_id = request.data.get("id").rstrip('/').split("/posts/")[-1]

  # Check if the post already exists and create it if it doesn’t
  # post, created = Post.objects.get_or_create(
  #     id=post_id,
  #     defaults={
  #         "author_id": author,
  #         "title": request.data.get("title"),
  #         "description": request.data.get("description"),
  #         "content": request.data.get("content"),
  #         "content_type": request.data.get("contentType"),
  #         "visibility": request.data.get("visibility"),
  #     }
  # )
  # filter for post
  # if it exists, replace it with the new one
  post = Post.objects.filter(id=post_id).first()
  if post:
      post.author_id = post_author
      post.title = request.data.get("title")
      post.description = request.data.get("description")
      post.content = request.data.get("content")
      post.content_type = request.data.get("contentType")
      post.visibility = request.data.get("visibility")
      post.save()
      
      # Post already exists, return a message or existing post data
      return Response(
          {"message": "Post already exists", "post": PostSerializer(post).data},
          status=status.HTTP_200_OK
      )
  else:
      post = Post.objects.create(
          id=post_id,
          author_id=post_author,
          title=request.data.get("title"),
          description=request.data.get("description"),
          content=request.data.get("content"),
          content_type=request.data.get("contentType"),
          visibility=request.data.get("visibility"),
      )
      serializer = PostSerializer(post)
      return Response(serializer.data, status=status.HTTP_201_CREATED)

def handle_comment_inbox(request, author, author_id):
    author = get_object_or_404(Author, id=author_id) #author is the one who made the comment
    # we already get the post its supposed to be added to from the request body
    # TODO: need to make author if they don't exist from another node. not get object or 404

    comment_data = request.data
    
    post_url = comment_data.get("post")
    if not post_url:
        return Response({"Error": "Post URL is required."}, status=status.HTTP_400_BAD_REQUEST)

    post_id = post_url.rstrip('/').split("/posts/")[-1]
    post = get_object_or_404(Post, id=post_id)

    # get author of commenter 
    author_of_comment = comment_data["author"]["id"]
    author_of_comment_id = author_of_comment.rstrip('/').split("/authors/")[-1]
    comment_id = comment_data["id"]

    if '/commented/' in comment_id:
        comment_id = comment_data["id"].rstrip('/').split('/commented/')[-1]
    elif '/comments/' in comment_id:
        comment_id = comment_data["id"].rstrip('/').split('/comments/')[-1]


    author_data = request.data["author"]

    # get or create remote author who made the comment
    comment_author, created = Author.objects.get_or_create(
        id=author_of_comment_id,
        defaults={
            "host": author_data['host'],
            "display_name": author_data['displayName'],
            "github": author_data.get('github', ''),
            "profile_image": author_data.get('profileImage', ''),
            "page": author_data['page'],
        }
    )

    comment = Comment.objects.filter(id=comment_id).first()
    if not comment:
        #creating the comment object
        comment_serializer = CommentSerializer(data=request.data)
        if comment_serializer.is_valid():
            comment_serializer.save(
                id=comment_id,
                author_id=comment_author,
                post_id=post
            )
    
        return Response(comment_serializer.data, status=status.HTTP_201_CREATED) 
    else:
        comment_serializer = CommentSerializer(comment)
        return Response(comment_serializer.data, status=status.HTTP_200_OK)    
        
def handle_like_inbox(request, author, author_id):
    #author who created the like
    author = get_object_or_404(Author, id=author_id)

    like_data = request.data

    object_url = like_data.get("object") #object can be either a comment or post
    if not object_url:
        return Response({"Error": "object URL is required."}, status=status.HTTP_400_BAD_REQUEST)

    # determine like was for post or comment
    if "/posts/" in object_url:
        # object is a post
        object_id = object_url.rstrip('/').split("/posts/")[-1]
        liked_object = get_object_or_404(Post, id=object_id)
        object_content_type = ContentType.objects.get_for_model(Post)
    elif "/commented/" in object_url:
        # object is a comment
        object_id = object_url.rstrip('/').split("/commented/")[-1]
        liked_object = get_object_or_404(Comment, id=object_id)
        object_content_type = ContentType.objects.get_for_model(Comment)
    else:
        return Response({"detail": "Invalid object URL format."}, status=status.HTTP_400_BAD_REQUEST)
    
    # get author of commenter 
    author_of_like = like_data["author"]["id"]
    author_of_like_id = author_of_like.rstrip('/').split("/authors/")[-1]

    author_data = request.data["author"]
    # get or create remote author who made the comment
    like_author, created = Author.objects.get_or_create(
        id=author_of_like_id,
        defaults={
            "host": author_data['host'],
            "display_name": author_data['displayName'],
            "github": author_data.get('github', ''),
            "profile_image": author_data.get('profileImage', ''),
            "page": author_data['page'],
        }
    )

    #check if user has already liked the object
    existing_like = Like.objects.filter(
        author_id=like_author,
        object_url=object_url
    ).first()

    if existing_like:
        return Response(LikeSerializer(existing_like).data, status=status.HTTP_200_OK) #if they've already liked, can't like again

    like_serializer = LikeSerializer(data=request.data) #asked chatGPT how to set the host in the serializer, need to add context 2024-11-02
    if like_serializer.is_valid():

        like_serializer.save(
            author_id=like_author,  
            object_id=liked_object.id,
            content_type=object_content_type,
            object_url=object_url
        )

        # #creating Inbox object to forward to correct inbox
        # post_host = object_url.split("//")[1].split("/")[0]
        # if post_host != request.get_host():
        #     # TODO: Part 3-5 post or comment not on our host, need to forward it to a remote inbox
        #     pass
        
        return Response(like_serializer.data, status=status.HTTP_201_CREATED)   
    else:
        return Response(like_serializer.errors, status=status.HTTP_400_BAD_REQUEST)