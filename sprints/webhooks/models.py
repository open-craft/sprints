import json

import requests
from django.db import models


class WebhookEvent(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

class Webhook(models.Model):
    payload_url = models.URLField()
    active = models.BooleanField()
    events = models.ManyToManyField(WebhookEvent)
    headers = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.payload_url

    def trigger(self, payload):
        requests.post(
            self.payload_url,
            data=json.dumps(payload),
            headers=self.headers if self.headers else {},
        )
