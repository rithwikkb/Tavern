from urllib.parse import urlparse
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from users.models import Author
from users.utils import validate_web_url


class AuthorSerializer(serializers.Serializer):
    type = serializers.CharField(default='author', read_only=True)
    id = serializers.SerializerMethodField()  # Full API URL for the author
    host = serializers.URLField() # The full API URL for the author's node
    displayName = serializers.CharField(source='display_name')
    github = serializers.CharField(required=False, allow_null=True, allow_blank=True)  # URL of the user's GitHub
    profileImage = serializers.CharField(required=False, source='profile_image', allow_null=True, allow_blank=True)
    page = serializers.CharField(required=False, allow_null=True, allow_blank=True) 
    description = serializers.CharField(required=False, default='No Description', allow_null=True, allow_blank=True)

    def get_id(self, author):
    # Constructs the URL based on the author's host and their UUID
       return f"{author.host.rstrip('/')}/authors/{author.id}"
    
    # https://dev.to/amanbothra/understanding-the-torepresentation-and-tointernalvalue-methods-in-the-django-rest-framework-naa want 'type' to be in serialized output but not part of model
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['type'] = 'author'  # Add 'type' to the representation

         # Ensure fields match specification
        data['displayName'] = data.pop('displayName', "")
        data['profileImage'] = data.pop('profileImage', "")
        
        return data
    
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        
        # Normalize the host field
        if 'host' in data:
            parsed_host = urlparse(data['host'])
            data['host'] = f"{parsed_host.scheme}://{parsed_host.netloc}"
        else:
            # if host is not provided, set to my host
            request = self.context.get('request')
            if request:
                scheme = request.scheme
                host = request.get_host()
                data['host'] = f"{scheme}://{host}"
        
        return data
    
class AuthorEditProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['display_name', 'github', 'profile_image']  # Only fields you want to update
    
    def validate_profile_image(self, value):
        # rendered as an <img> everywhere the author appears, so keep it a plain web URL
        if value:
            try:
                validate_web_url(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value

    def validate_github(self, value):
        if value:
            try:
                validate_web_url(value)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value

    def update(self, instance, validated_data):
        # Update the author instance with the provided validated data
        instance.display_name = validated_data.get('display_name', instance.display_name)
        instance.github = validated_data.get('github', instance.github)
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()  # Save the updated instance to the database
        return instance

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    