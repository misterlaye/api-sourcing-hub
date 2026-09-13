from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, User


class CustomUserCreationForm(UserCreationForm):
    """
    UserCreationForm de base est lié au modèle User de contrib.auth.
    On le rebranche sur notre modèle custom pour l'utiliser dans l'admin.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = (
        'email', 'role', 'status', 'is_profile_complete',
        'is_staff', 'is_active', 'date_joined',
    )
    list_filter = ('role', 'status', 'is_staff', 'is_active', 'is_profile_complete')
    search_fields = ('email',)
    ordering = ('email',)
    readonly_fields = ('date_joined', 'last_login', 'last_invited_at')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Rôle & statut'), {'fields': ('role', 'status', 'is_profile_complete', 'last_invited_at')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Dates importantes'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'status'),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Un journal d'audit ne doit pas pouvoir être modifié ni créé
    manuellement depuis l'admin : seule la lecture (et éventuellement
    la suppression pour purge) est autorisée.
    """
    list_display = ('created_at', 'actor', 'action', 'status', 'target', 'ip_address')
    list_filter = ('action', 'status', 'created_at')
    search_fields = ('actor__email', 'target', 'ip_address')
    autocomplete_fields = ('actor',)
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
