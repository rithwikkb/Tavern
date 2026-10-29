from rest_framework import status
from rest_framework.response import Response

from users.models import Follows
from users.utils import is_request_author
from .serializers import FollowSerializer

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

  # the logged-in user can only send follow requests as themselves, to the inbox owner
  if not is_request_author(request, actor_id):
      return Response({"error": "You can only send follow requests as yourself."}, status=status.HTTP_403_FORBIDDEN)
  if object_id != str(author.id):
      return Response({"error": "The follow request's object must be the inbox owner."}, status=status.HTTP_400_BAD_REQUEST)
  if object_id == actor_id:
      return Response({"error": "You can't follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

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
