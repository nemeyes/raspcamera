from ast import Delete
from nis import match
from telnetlib import STATUS
from unicodedata import name
from urllib import response
from warnings import catch_warnings
from cairo import Status
from django.forms import DateTimeField, NullBooleanField
from django.shortcuts import render
from rest_framework import viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, JsonResponse
from time import timezone
import uuid
import time
import datetime
import os


from .models import Stream, StoreFile
from .serializers import StreamSerializer, StreamResponseSerializer
from .serializers import StoreFileSerializer, StoreFileResponseSerializer
from .gStreamer import gStreamerWrapper, Error


class StreamViewSet(viewsets.ModelViewSet):
    queryset = Stream.objects.all()
    serializer_class = StreamSerializer


class StreamStartAPIView(APIView):
    def get(self, request):
        try:
            request_id = request.GET["requestid"]
        except:
            return JsonResponse({"error": "Key Error"}, status=400)

        isInvailedParams = False
        try:
            width = int(request.GET["width"])
        except:
            width = 1280
        if width < 1 or width > 1920:
            isInvailedParams = True

        try:
            height = int(request.GET["height"])
        except:
            height = 720
        if height < 1 or height > 1080:
            isInvailedParams = True

        try:
            fps = int(request.GET["fps"])
        except:
            fps = 30
        if fps < 1 or fps > 30:
            isInvailedParams = True

        try:
            brightness = int(request.GET["brightness"])
        except:
            brightness = 50
        if brightness < 0 or brightness > 100:
            isInvailedParams = True

        try:
            saturation = int(request.GET["saturation"])
        except:
            saturation = 0
        if saturation < 0 or saturation > 100:
            isInvailedParams = True

        try:
            bitrate = int(request.GET["bitrate"])
        except:
            bitrate = 5000000  # 5Mbits/s
        if bitrate < 200000 or bitrate > 20000000:
            isInvailedParams = True

        if isInvailedParams == True:
            return JsonResponse({"error": "Invailed Parameter Error"}, status=400)

        # gstreamer streaming start
        gstWrapper = gStreamerWrapper.instance()
        gstWrapper.SetStreamInfo(width, height, fps, brightness, saturation, bitrate)
        result = gstWrapper.StreamingStart()
        print("StreamingStart %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "Stream Start Error", "code": result.value}, status=400)

        newStream = Stream.objects.create(
            name=uuid.uuid4(),
            requestFrom=request_id,
        )
        responsedata = StreamResponseSerializer(newStream)
        return Response(responsedata.data)

    def post(self, request):
        try:
            request_id = request.data["requestid"]
        except:
            return JsonResponse({"error": "Key Error"}, status=400)

        isInvailedParams = False
        try:
            width = int(request.data["width"])
        except:
            width = 1280
        if width < 1 or width > 1920:
            isInvailedParams = True

        try:
            height = int(request.data["height"])
        except:
            height = 720
        if height < 1 or height > 1080:
            isInvailedParams = True

        try:
            fps = int(request.data["fps"])
        except:
            fps = 30
        if fps < 1 or fps > 30:
            isInvailedParams = True

        try:
            brightness = int(request.data["brightness"])
        except:
            brightness = 50
        if brightness < 0 or brightness > 100:
            isInvailedParams = True

        try:
            saturation = int(request.data["saturation"])
        except:
            saturation = 0
        if saturation < 0 or saturation > 100:
            isInvailedParams = True

        try:
            bitrate = int(request.data["bitrate"])
        except:
            bitrate = 10000000  # 10Mbits/s
        if bitrate < 100000 or bitrate > 20000000:
            isInvailedParams = True

        if fps <= 10:
            bitrate = bitrate / 2

        if isInvailedParams == True:
            return JsonResponse({"error": "Invailed Parameter Error"}, status=400)

        # gstreamer streaming start
        gstWrapper = gStreamerWrapper.instance()
        gstWrapper.SetStreamInfo(width, height, fps, brightness, saturation, bitrate)
        result = gstWrapper.StreamingStart()
        print("StreamingStart %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "Stream Start Error", "code": result.value}, status=400)

        newStream = Stream.objects.create(
            name=uuid.uuid4(),
            requestFrom=request_id,
        )
        responsedata = StreamResponseSerializer(newStream)
        return Response(responsedata.data)


class StreamStopAPIView(APIView):
    def get(self, request):
        if Stream.objects.count() == 0:
            return JsonResponse({"error": "No Matching Stream"}, status=400)

        matchingStream = Stream.objects.last()

        # gstreamer streaming stop
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StreamingStop()
        time.sleep(1)
        gstWrapper.CaptureLastImage()
        print("StreamingStop %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "Stream Stop Error", "code": result.value}, status=400)

        matchingStream.setEndTime()

        return JsonResponse({"error": "OK"}, status=200)

    def post(self, request):
        if Stream.objects.count() == 0:
            return JsonResponse({"error": "No Matching Stream"}, status=400)

        matchingStream = Stream.objects.last()

        # gstreamer streaming stop
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StreamingStop()
        print("StreamingStop %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "Stream Stop Error", "code": result.value}, status=400)

        matchingStream.setEndTime()

        return JsonResponse({"error": "OK"}, status=200)


class LastImageView(APIView):
    def get(self, reqiest):
        try:
            lastImage = open("lastimage.jpg", "rb")
        except:
            return JsonResponse(
                {"error": "LastImage is not found", "code": Error.Store_Inviled_FilePath.value}, status=400
            )
        responseLastImage = FileResponse(lastImage)
        return responseLastImage


class StoreFileViewSet(viewsets.ModelViewSet):
    queryset = StoreFile.objects.all()
    serializer_class = StoreFileSerializer


class StoreFileStartAPIView(APIView):
    def get(self, request):
        try:
            streamName = request.GET["name"]
        except:
            return JsonResponse({"error": "Key Error"}, status=400)

        try:
            requestURL = request.GET["URL"]
        except:
            requestURL = "rtsp://localhost:8554/raspiVideo"

        path = os.path.expanduser("~") + "/raspistream/record"
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        targetPath = path + "/" + streamName + ".mp4"
        print("Geterated Filename %s" % targetPath)

        # gstreamer streaming start
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StoreFileStart(targetPath, requestURL)
        print("StoreFileStart %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "StoreFile Start Error", "code": result.value}, status=400)

        newStoreFile = StoreFile.objects.create(
            name=streamName,
            filepath=targetPath,
        )
        responsedata = StoreFileResponseSerializer(newStoreFile)
        return Response(responsedata.data)

    def post(self, request):
        try:
            streamName = request.data["name"]
        except:
            return JsonResponse({"error": "Key Error"}, status=400)

        path = os.path.expanduser("~") + "/raspistream/record"
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        targetPath = path + "/" + streamName + ".mp4"
        print("Geterated Filename %s" % targetPath)

        # gstreamer streaming start
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StoreFileStart(targetPath)
        print("StoreFileStart %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "StoreFile Start Error", "code": result.value}, status=400)

        newStoreFile = StoreFile.objects.create(
            name=streamName,
            filepath=targetPath,
        )
        responsedata = StoreFileResponseSerializer(newStoreFile)
        return Response(responsedata.data)


class StoreFileStopAPIView(APIView):
    def get(self, request):
        # gstreamer streaming stop
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StoreFileStop()
        print("StoreFileStop %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "StoreFile Stop Error", "code": result.value}, status=400)

        matchingStoreFiles = StoreFile.objects.last()
        matchingStoreFiles.setEndTime()

        return JsonResponse({"error": "OK"}, status=200)

    def post(self, request):
        # gstreamer streaming stop
        gstWrapper = gStreamerWrapper.instance()
        result = gstWrapper.StoreFileStop()
        print("StoreFileStop %s" % result)
        if result != Error.Success:
            return JsonResponse({"error": "StoreFile Stop Error", "code": result.value}, status=400)

        matchingStoreFiles = StoreFile.objects.last()
        matchingStoreFiles.setEndTime()

        return JsonResponse({"error": "OK"}, status=200)


class StatusAPIView(APIView):
    def get(self, request):
        # status
        gstWrapper = gStreamerWrapper.instance()

        responseJSON = {"Streaming": False, "Recording": False}
        responseJSON["Streaming"] = gstWrapper.IsStreaming
        responseJSON["Recording"] = gstWrapper.IsStoreFile
        return JsonResponse(responseJSON)


# ===============================================================
# === Erase Stored File Scheduler
# ===============================================================

from apscheduler.schedulers.background import BackgroundScheduler

eraseStoreFileScheduler = BackgroundScheduler()

# @eraseStoreFileScheduler.scheduled_job('interval', seconds=5, id='eraseStoreFile') #test
@eraseStoreFileScheduler.scheduled_job("cron", hour="03", minute="30", id="eraseStoreFile")
def eraseStroedFile():
    print(f'eraseStroedFile : {time.strftime("%Y-%m-%d %H:%M:%S")}')
    currentdate = datetime.datetime.today()
    targetdate = currentdate - datetime.timedelta(days=2)
    targetdate.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
    print(f'delete target items : {targetdate.strftime("%Y-%m-%d %H:%M:%S")}')
    eraseTargets = StoreFile.objects.filter(start_date__lte=targetdate).filter(isDeleted=False)
    if eraseTargets.count() == 0:
        print("no target file")
        return

    for storefileinfo in eraseTargets:
        targetfile = storefileinfo.filepath
        storefileinfo.setDeleteFile(True)
        print("erase target file flag set " + targetfile)
        if os.path.exists(targetfile):
            print("erase target file " + targetfile)
            os.remove(targetfile)


eraseStoreFileScheduler.start()
