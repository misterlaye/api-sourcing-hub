from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt_views import (
    JWTLoginView as LoginView,
)
from .jwt_views import (
    LogoutView,
)
from .views import (
    ActivateAccountView,
    CompleteProfileView,
    ConfirmPasswordResetView,
    RequestPasswordResetView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

app_name = 'accounts'

urlpatterns = [
    path('', include(router.urls)),
    
    path('activate/', ActivateAccountView.as_view(), name='account-activate'),
    
    path('profile/complete/', CompleteProfileView.as_view(), name='profile-complete'),
    
    path('password-reset/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    
    path('password-reset/confirm/<str:uid>/<str:token>/', ConfirmPasswordResetView.as_view(), name='password-reset-confirm'),

    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
