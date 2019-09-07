from rest_framework.routers import DefaultRouter

from sprints.dashboard.views import (
    CellViewSet,
    CompleteSprintViewSet,
    CreateNextSprintViewSet,
    DashboardViewSet,
)

app_name = "dashboard"
router = DefaultRouter()
router.register(r'cells', CellViewSet, basename='cells')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'create_next_sprint', CreateNextSprintViewSet, basename='create_next_sprint')
router.register(r'complete_sprint', CompleteSprintViewSet, basename='complete_sprint')
urlpatterns = router.urls
