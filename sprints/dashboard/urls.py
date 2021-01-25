from rest_framework.routers import DefaultRouter

from sprints.dashboard.views import (
    CompleteSprintViewSet,
    DashboardViewSet,
)

app_name = "dashboard"
router = DefaultRouter()
router.register(r"", DashboardViewSet, basename="dashboard")
router.register(r"complete_sprint", CompleteSprintViewSet, basename="complete_sprint")
urlpatterns = router.urls
