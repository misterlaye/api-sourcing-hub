from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Manager personnalisé où l'email est l'identifiant unique
    pour l'authentification à la place du username.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        
        email = self.normalize_email(email)
        
        # Par défaut, on s'assure qu'un utilisateur créé par code est 'INVITED'
        extra_fields.setdefault('status', 'INVITED')
        
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # Très important niveau sécurité : un compte sans mot de passe ne doit pas pouvoir se connecter
            user.set_unusable_password()
            
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et enregistre un SuperUser.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', 'ACTIVE') # Le superuser est actif direct
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser doit avoir is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
