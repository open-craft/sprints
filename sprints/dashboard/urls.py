from rest_framework.routers import DefaultRouter

from sprints.dashboard.views import CellViewSet, DashboardViewSet

app_name = "dashboard"
router = DefaultRouter()
router.register(r'cells', CellViewSet, basename='cells')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
urlpatterns = router.urls
