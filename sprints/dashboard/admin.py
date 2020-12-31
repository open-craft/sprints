from django.contrib import admin
from sprints.dashboard.models import Webhook, WebhookEvent

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    pass

@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    pass
