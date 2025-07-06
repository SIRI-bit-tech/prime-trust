from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from .serializers import UserDetailSerializer, PasswordChangeSerializer
from accounts.models import UserProfile
from accounts.utils import send_verification_email, verify_code
import random
import string

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user information."""
    username_field = 'email'  # Use email as the username field
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        # Get email and password from the request
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise ValidationError("Email and password are required")
        
        # Authenticate the user
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        if not user:
            raise ValidationError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise ValidationError("Account is deactivated")
        
        # Generate and send login verification code
        login_code = ''.join(random.choices(string.digits, k=6))
        user.login_code = login_code
        user.login_code_created_at = timezone.now()
        user.save()
        
        # Send the code via email
        send_verification_email(user.email, login_code, is_login=True)
        
        # Return a temporary response indicating verification needed
        return {
            'detail': 'Login code sent to your email. Please verify to complete login.',
            'requires_verification': True,
            'user_id': user.id
        }


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view with email verification."""
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
def verify_login_api(request):
    """Verify login code and return JWT tokens."""
    user_id = request.data.get('user_id')
    code = request.data.get('code')
    
    if not user_id or not code:
        return Response(
            {'error': 'User ID and code are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(id=user_id)
        if verify_code(user.email, code):
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Add custom claims
            access_token['username'] = user.username
            access_token['email'] = user.email
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': UserDetailSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Invalid or expired code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid user'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """Logout by blacklisting the refresh token."""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response(
            {'message': 'Successfully logged out'}, 
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Invalid token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_api(request):
    """Get current user profile."""
    serializer = UserDetailSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_api(request):
    """Update current user profile."""
    user = request.user
    serializer = UserDetailSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """Change user password."""
    serializer = PasswordChangeSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        # Check old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Old password is incorrect'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'}, 
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def resend_login_code_api(request):
    """Resend login verification code."""
    user_id = request.data.get('user_id')
    
    if not user_id:
        return Response(
            {'error': 'User ID is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Generate new code
        login_code = ''.join(random.choices(string.digits, k=6))
        user.login_code = login_code
        user.login_code_created_at = timezone.now()
        user.save()
        
        # Send the code
        send_verification_email(user.email, login_code, is_login=True)
        
        return Response(
            {'message': 'Login code sent successfully'}, 
            status=status.HTTP_200_OK
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid user'}, 
            status=status.HTTP_400_BAD_REQUEST
        ) 