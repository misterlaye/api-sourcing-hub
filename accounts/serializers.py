from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour la liste, le détail et la modification des utilisateurs.

    Expose les champs nécessaires à l'affichage côté frontend.
    Le mot de passe et les tokens ne sont jamais inclus.
    """
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'status', 'is_active', 'phone_number', 'is_profile_complete',
            'date_joined', 'last_invited_at'
        ]
        read_only_fields = ['id', 'date_joined', 'last_invited_at']


class AccountActivationSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        # 1. Vérifier que les deux mots de passe correspondent
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Les mots de passe ne correspondent pas."}
            )
        
        # 2. Vérifier la robustesse du mot de passe
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return attrs


class AdminUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'role']

    def validate_role(self, value):
        actor = self.context['request'].user

        if not actor.is_authenticated:
            raise serializers.ValidationError(
                "Vous devez être authentifié pour effectuer cette action."
            )

        if actor.role != User.Role.ADMIN:
            raise serializers.ValidationError(
                "Seul un administrateur peut attribuer un rôle."
            )

        return value



class ProfileCompletionSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    # token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Les mots de passe ne correspondent pas."})
        
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        try:
            validate_password(attrs['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
            
        return attrs
