import urllib
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import FollowSerializer
from users.models import Author, Follows
from django.shortcuts import get_object_or_404
from rest_framework import status  
from .utils import handle_follow_request
from users.utils import is_fqid, is_request_author

class InboxView(APIView):
    """
    Handle incoming requests to the inbox.
    """
    
    def post(self, request, author_id):
        try:
            # check if author_id is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_id):
                author_id = urllib.parse.unquote(author_id)
                if not author_id.endswith('/'):
                    author_id += '/'
                author_id = Author.objects.get(url=author_id).id
        except:
            return Response({"error": "InboxView - POST - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        
        object_type = request.data.get('type')
        author = get_object_or_404(Author, id=author_id)

        # only follow requests are delivered through the inbox
        if object_type == "follow":
            return handle_follow_request(request, author)

        return Response({"error": f"Unsupported inbox object type: {object_type}"}, status=status.HTTP_400_BAD_REQUEST)

class FollowRequests(APIView):
    """
    get follow requests for user
    """
    def get(self, request, author_id):
        try:
            # check if author_id is a URL (FQID) or a uuid (SERIAL)
            if is_fqid(author_id):
                author_id = urllib.parse.unquote(author_id)
                if not author_id.endswith('/'):
                    author_id += '/'
                author_id = Author.objects.get(url=author_id).id
        except:
            return Response({"error": "FollowRequests - GET - Invalid FQID or SERIAL."}, status=status.HTTP_400_BAD_REQUEST)
        author = get_object_or_404(Author, id=author_id)
        if not is_request_author(request, author.id):
            return Response({"error": "You can only view your own follow requests."}, status=status.HTTP_403_FORBIDDEN)
        pending_follow_requests = Follows.objects.filter(followed_id=author, status='PENDING')

        serialized_data = FollowSerializer(pending_follow_requests, many=True).data
        for follow_data in serialized_data:
            follow_data['type'] = 'follow'
        return Response(serialized_data, status=200)