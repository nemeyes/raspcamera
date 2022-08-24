from time import timezone
from xmlrpc.client import Boolean
from django.db import models
from django.utils import timezone


class Stream(models.Model):
    name = models.CharField(max_length=200, help_text="stream name")
    requestFrom = models.CharField(max_length=200, help_text="stream request id")
    start_date = models.DateTimeField(auto_now_add=True, help_text="date time start")
    end_date = models.DateTimeField(help_text="date time end", blank=True, null=True)

    def __str__(self) -> str:
        return self.name

    def setEndTime(self):
        self.end_date = timezone.now()
        self.save()


class StoreFile(models.Model):
    name = models.CharField(max_length=256, help_text="stored file name")
    filepath = models.CharField(max_length=4096, help_text="stored file real path name")
    start_date = models.DateTimeField(auto_now_add=True, help_text="date time start")
    end_date = models.DateTimeField(help_text="date time end", blank=True, null=True)
    isDeleted = models.BooleanField(help_text="Deleted flags", default=False)

    def __str__(self) -> str:
        return self.name

    def setEndTime(self):
        self.end_date = timezone.now()
        self.save()

    def setDeleteFile(self, isDelete: Boolean):
        self.isDeleted = isDelete
        self.save()
