from django.conf.urls import url
from django.urls import path

from sprints.users.api import (
    RegistrationAPI,
    LoginAPI,
    UserAPI,
)
from sprints.users.views import (
    user_redirect_view,
    user_update_view,
    user_detail_view,
)

app_name = "users"
urlpatterns = [
    url("^auth/register/$", RegistrationAPI.as_view()),
    url("^auth/login/$", LoginAPI.as_view()),
    url("^auth/user/$", UserAPI.as_view()),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
