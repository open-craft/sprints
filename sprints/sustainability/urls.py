from rest_framework.routers import DefaultRouter

from sprints.sustainability.views import SustainabilityDashboardViewSet

app_name = "sustainability"
router = DefaultRouter()
router.register(r"dashboard", SustainabilityDashboardViewSet, basename="dashboard")
urlpatterns = router.urls
