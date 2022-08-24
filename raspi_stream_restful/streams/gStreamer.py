from warnings import catch_warnings
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
gi.require_version("GstVideo", "1.0")
gi.require_version("GstBase", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import GObject, Gst, Gio, GstVideo, GstRtspServer, GLib
import platform

from enum import Enum


class SingletonInstane:
    __instance = None

    @classmethod
    def __getInstance(cls):
        return cls.__instance

    @classmethod
    def instance(cls, *args, **kargs):
        cls.__instance = cls(*args, **kargs)
        cls.instance = cls.__getInstance
        return cls.__instance


class Error(Enum):
    Success = 0

    Stream_Unknown = 1000
    Stream_Not_Running = 1001
    Stream_Already_Running = 1002
    Stream_Start_Failed = 1003

    Store_Unknown = 2000
    Store_Not_Running = 2001
    Store_Already_Running = 2002
    Store_Disk_Full = 2003
    Store_Inviled_FilePath = 2004

    Unknown = 3000


import time
import os.path
import subprocess
import signal
import sys
from threading import Thread, Lock

cam_mutex = Lock()

Gst.init(None)
GObject.MainLoop()


class StreamServer:
    def __init__(self, device, file, port, name, width, height, codec):
        self.mainloop = GObject.MainLoop()
        self.server = GstRtspServer.RTSPServer()
        self.mounts = self.server.get_mount_points()

        self.device = device
        self.file = file

        self.port = port
        self.name = name

        self.factory = GstRtspServer.RTSPMediaFactory()
        # Factory must be shared to allow multiple connections
        self.factory.set_shared(True)
        self.factory.set_eos_shutdown(True)
        self.context_id = 0
        self.running = False
        self.stayAwake = True

        GObject.threads_init()
        print("StreamServer initialized")

        self.codec_options = {0: "h264", 1: "MJPEG"}
        self.codec = codec

        # Declaring stream settings and initialize with safe default values
        self.bitrate_range = [200000, 20000000]
        self.bitrate = 10000000

        # dynamic range compression
        self.drc_options = {0: "off", 1: "low", 2: "medium", 3: "high"}
        self.drc = 3

        # key frame control (autmoatic = -1)
        self.h264_i_frame_period_range = [-1, 60]
        # self.h264_i_frame_period = 15
        self.h264_i_frame_period = 60

        # Shutter speed
        # 	0: 				Automatic (default)
        # 	1 to 10000000:	Fixed shutter speed in microseconds
        self.shutter_range = [0, 10000001]
        self.shutter = 0

        # ISO level
        # 	0:				Automatic (default)
        # 	100 to 3200:	Fixed ISO mode
        self.iso_options = {0: "auto", 100: "ISO 100", 200: "ISO 200", 400: "ISO 400", 800: "ISO 800"}
        self.iso = 0

        ##################################################################################################################################################################
        # Sharpness
        # 	0 to 100: Tweak sharpness filter (default=0)
        self.sharpness_range = [0, 100]
        self.sharpness = 0

        ##################################################################################################################################################################
        # Birghtness
        # 	0 to 100: Tweak brightness (default=50)
        self.brightness_range = [0, 100]
        self.brightness = 50

        ##################################################################################################################################################################
        # Saturation
        # 	0 to 100: Tweak saturation (default=0)
        self.saturation_range = [0, 100]
        self.saturation = 0

        ##################################################################################################################################################################
        # Contrast
        # 	0 to 100: Tweak contrast (default=0 for video stream)
        self.contrast_range = [0, 100]
        self.contrast = 0

        ##################################################################################################################################################################
        # Frames per second
        # 	15 to 90: >30fps only available at 640x480
        self.fps = 30
        self.fps_range = [1, 90]

        self.horizontal_mirroring = False
        self.vertical_mirroring = False
        self.video_stabilisation = False

        # White balance
        # 	000:			Off
        # 	001:			Automatic (default)
        # 	002:			sunlight
        # 	003:			Cloudy
        # 	004:			Shade
        # 	005:			Tungsten bulp
        # 	006:			Fluorescent
        # 	007:			Incandescent
        # 	008:			Xenon flash
        # 	009:			Horizon
        self.white_balance_options = {
            0: "Off",
            1: "auto",
            2: "sunlight",
            3: "cloudy",
            4: "shade",
            5: "tungsten",
            6: "flourescent",
            7: "incandescent",
            8: "xenon",
            9: "horizon",
        }
        self.white_balance = 1

        # RGB channels might be controlled individually, if white balance mode is "Off"
        self.gain_red_range = [0.0, 8.0]
        self.gain_red = 1.0
        self.gain_green_range = [0.0, 8.0]
        self.gain_green = 1.0
        self.gain_blue_range = [0.0, 8.0]
        self.gain_blue = 1.0

        self.width_options = {0: 640, 1: 800, 2: 1024, 3: 1280, 4: 1640, 5: 1920}
        self.width = width
        self.height_options = {0: 480, 1: 600, 2: 720, 3: 768, 4: 1024, 5: 1232, 6: 1080}
        self.height = height

        self.rotation = 0

        self.configDate = 0

    def exit_gracefully(self, signum, frame):
        self.stop()
        self.stayAwake = False

    def check_range(self, value, value_range):
        return value >= value_range[0] and value <= value_range[1]

    def check_option(self, option, options):
        return options.has_key(option)

    def setoptions(self, width=1280, height=720, framerate=30, brightness=50, saturation=0, bitrate=10000000):
        self.width = width
        self.height = height
        self.fps = framerate
        self.bitrate = bitrate
        self.brightness = brightness
        self.saturation = saturation

    def launch(self):
        print("StreamServer.launch")
        if self.running:
            print("StreamServer.launch called on running instance.")
            self.stop()  # Need to stop any instances first

        if self.device == "picam":
            launch_str = (
                "( rpicamsrc sensor-mode=1920x1080 preview=false bitrate="
                # "( rpicamsrc sensor-mode=1920x1080 inline-headers=true preview=false bitrate="
                + str(self.bitrate)
                + " keyframe-interval="
                + str(self.h264_i_frame_period)
                + " drc="
                + str(self.drc)
                + " image-effect=denoise shutter-speed="
                + str(self.shutter)
                + " iso="
                + str(self.iso)
                + " brightness="
                + str(self.brightness)
                + " contrast="
                + str(self.contrast)
                + " saturation="
                + str(self.saturation)
                + " sharpness="
                + str(self.sharpness)
                + " awb-mode="
                + str(self.white_balance)
                + " rotation="
                + str(self.rotation)
                + " hflip="
                + str(self.horizontal_mirroring)
                + " vflip="
                + str(self.vertical_mirroring)
                + " video-stabilisation="
                + str(self.video_stabilisation)
            )
            if self.white_balance == 0:
                print("Using custom white balance settings")
                launch_str = launch_str + "awb-gain-red=" + self.gain_red
                launch_str = launch_str + "awb-gain-green=" + self.gain_green
                launch_str = launch_str + "awb-gain-blue=" + self.gain_blue

            # Completing the pipe
            if self.codec == 0:
                launch_str = (
                    launch_str
                    + " ! video/x-h264, profile=baseline, framerate="
                    + str(self.fps)
                    + "/1, width="
                    + str(self.width)
                    + ", height="
                    + str(self.height)
                    # + " ! h264parse"
                    # + " ! tee name=t t. ! queue name=outqueue ! rtph264pay name=pay0 pt=96 ! udpsink port=9982 host=127.0.0.1 name=outsink "
                    # + "  t. ! rtph264pay name=pay1 pt=96 )"
                    + " ! h264parse ! rtph264pay config-interval=-1 aggregate-mode=zero-latency name=pay0 pt=96 )"
                )
            elif self.codec == 1:
                launch_str = (
                    launch_str
                    + " ! image/jpeg, framerate="
                    + str(self.fps)
                    + "/1, width="
                    + str(self.width)
                    + ", height="
                    + str(self.height)
                    + " ! jpegparse ! rtpjpegpay name=pay0 pt=96 )"
                )
            else:
                print("Illegal codec")

        else:  # USB Camera
            # Ignore most of the parameters
            print("USB camera ignored most of the parameters")
            platformname = platform.system()
            if platformname == "Darwin":
                launch_str = "( avfvideosrc "
                launch_str = (
                    launch_str
                    + " ! video/x-raw,width="
                    + str(self.width)
                    + ",height="
                    + str(self.height)
                    + ",framerate="
                    + str(self.fps)
                    + "/1 ! clockoverlay ! videoconvert ! x264enc tune=zerolatency bitrate="
                    + str(self.bitrate)
                    + " speed-preset=superfast ! video/x-h264,profile=baseline ! h264parse"
                    + " ! tee name=t \
                        t. ! queue name=outqueue ! rtph264pay name=pay1 pt=96 ! udpsink port=9982 host=127.0.0.1 name=outsink "
                    + " t. ! rtph264pay name=pay0 pt=96 )"
                )
            else:
                launch_str = (
                    "( v4l2src device="
                    + self.device
                    + " brightness="
                    + str(self.brightness)
                    + " contrast="
                    + str(self.contrast)
                    + " saturation="
                    + str(self.saturation)
                )
                launch_str = (
                    launch_str
                    + " ! video/x-raw,width="
                    + str(self.width)
                    + ",height="
                    + str(self.height)
                    + ",framerate="
                    + str(self.fps)
                    + "/1 ! clockoverlay ! omxh264enc target-bitrate="
                    + str(self.bitrate)
                    + " control-rate=variable ! video/x-h264,profile=baseline ! h264parse "
                    + "! rtph264pay name=pay0 pt=96 )"
                )
        # launch_str = '( v4l2src device='+self.device+' brightness='+str(self.brightness)+' contrast='+str(self.contrast)+' saturation='+str(self.saturation)
        # launch_str = launch_str + ' ! video/x-h264,width='+str(self.width)+',height='+str(self.height)+',framerate='+str(self.fps)+'/1 ! clockoverlay ! h264parse ! rtph264pay name=pay0 pt=96 )'

        print(launch_str)
        cam_mutex.acquire()
        try:
            print("Starting service on port " + str(self.port) + " at url /" + self.name)
            print("Shared rtsp media factory - " + str(self.factory.is_shared()))
            self.factory.set_launch(launch_str)
            self.server.set_service(str(self.port))
            self.mounts.add_factory("/" + str(self.name), self.factory)
            self.context_id = self.server.attach(None)

            # mainloop.run()
            self.mainthread = Thread(target=self.mainloop.run)
            self.mainthread.daemon = True
            self.mainthread.start()
            self.running = True
        finally:
            cam_mutex.release()
        print("Running RTSP Server")

    def disconnect_all(self, a, b):
        return GstRtspServer.RTSPFilterResult.REMOVE

    def stop(self):
        if self.running:
            print("Suspending RTSP Server")
            cam_mutex.acquire()
            try:
                self.server.client_filter(self.disconnect_all)
                time.sleep(0.3)
                self.mainloop.quit()
                self.mainthread.join()
                self.mounts.remove_factory("/" + str(self.name))
                GLib.Source.remove(self.context_id)
                self.running = False
            finally:
                cam_mutex.release()


class gStreamerWrapper(SingletonInstane):

    IsStreaming = False
    IsStoreFile = False

    def __init__(self):
        self.IsStreaming = False
        self.IsStoreFile = False
        self.width = 1920
        self.height = 1080
        self.port = 8554
        self.streamName = "raspiVideo"

        platformname = platform.system()
        print(platformname)

        if platformname == "Darwin":
            self.makeDarwinRecordPipeline()
        else:
            self.makeRaspiRecordPipeline()

        recordbus = self.recordpipe.get_bus()
        recordbus.add_signal_watch()
        recordbus.enable_sync_message_emission()
        recordbus.connect("message", self.on_message_for_record)
        recordbus.connect("sync-message::element", self.on_sync_message_for_record)

        # self.streamRTSPServer = StreamServer("/dev/video0", "", 8554, "raspiVideo", 1280, 720, "H264")
        if platformname == "Darwin":
            self.width = 1280
            self.height = 720
            self.streamRTSPServer = StreamServer(
                "/dev/video0", "", self.port, self.streamName, self.width, self.height, 0
            )
        else:
            self.streamRTSPServer = StreamServer(
                "picam", "", self.port, self.streamName, self.width, self.height, 0
            )

    def makeDarwinRecordPipeline(self):
        # Set up the gstreamer pipeline
        self.recordpipe = Gst.Pipeline.new("StreamStore")
        recordsource = Gst.ElementFactory.make("udpsrc", "recordsrc")
        # recordsource.set_property("host", "localhost")
        recordsource.set_property("port", 9982)

        capsString = "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96"
        inputCaps = Gst.Caps.from_string(capsString)
        inputCapsFilter = Gst.ElementFactory.make("capsfilter", "filter")
        inputCapsFilter.set_property("caps", inputCaps)

        recordqueue = Gst.ElementFactory.make("queue", "recvqueue")

        recordrtph264depay = Gst.ElementFactory.make("rtph264depay", "rtph264depay")
        recordh264parse = Gst.ElementFactory.make("h264parse", "h264parse")

        recordmp4mux = Gst.ElementFactory.make("mp4mux", "mp4mux")

        recordfilesink = Gst.ElementFactory.make("filesink", "filesink")
        recordfilesink.set_property("location", "default.mp4")
        # recordfilesink.set_property("sync", "false")

        if (
            not self.recordpipe
            or not recordsource
            or not inputCapsFilter
            or not recordqueue
            or not recordrtph264depay
            or not recordh264parse
            or not recordmp4mux
            or not recordfilesink
        ):
            print("ERROR: Not all elements could be created.")

        self.recordpipe.add(
            recordsource,
            inputCapsFilter,
            recordqueue,
            recordrtph264depay,
            recordh264parse,
            recordmp4mux,
            recordfilesink,
        )

        print("#--------------------------------------------------")

        ret = recordsource.link(inputCapsFilter)
        print("record source link inpurCapsFilters " + str(ret))
        ret = inputCapsFilter.link(recordqueue)
        print("record inputCapsFilter link recordqueue " + str(ret))
        ret = recordqueue.link(recordrtph264depay)
        print("recordqueue link record rtph264depay " + str(ret))
        ret = recordrtph264depay.link(recordh264parse)
        print("record rtph264depay link record h264parse " + str(ret))

        ret = recordh264parse.link(recordmp4mux)
        print("record h264parse link recordmp4mux " + str(ret))
        ret = recordmp4mux.link(recordfilesink)
        print("record mp4mux link record filesink " + str(ret))

        print("#--------------------------------------------------")

    def makeDarwinPipeline(self):
        self.source = Gst.ElementFactory.make("avfvideosrc", "camsource")
        self.source.set_property("do-timestamp", "true")

        capsString = "video/x-raw,width=1280,height=720,framerate=30/1"
        inputCaps = Gst.Caps.from_string(capsString)
        inputCapsFilter = Gst.ElementFactory.make("capsfilter", "filter")
        inputCapsFilter.set_property("caps", inputCaps)

        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        encoder = Gst.ElementFactory.make("x264enc", "encoder")
        encoder.set_property("tune", "zerolatency")
        encoder.set_property("bitrate", 800)
        encoder.set_property("speed-preset", "superfast")

        capsEncoderString = "video/x-h264, mapping=/stream"
        encoderCaps = Gst.Caps.from_string(capsEncoderString)
        encoderCapsFilter = Gst.ElementFactory.make("capsfilter", "filter")
        encoderCapsFilter.set_property("caps", encoderCaps)

        rtph264pay = Gst.ElementFactory.make("rtph264pay", "rtph264pay")
        rtph264pay.set_property("pt", 96)
        rtph264pay.set_property("config-interval", 1)

        h264parse = Gst.ElementFactory.make("h264parse", "h264parse")

        self.teesplit = Gst.ElementFactory.make("tee", "teesplit")

        self.queueforstream = Gst.ElementFactory.make("queue", "vidqueue")
        self.queueforstream.set_property("leaky", 1)

        udpsink = Gst.ElementFactory.make("udpsink", "outsink")
        udpsink.set_property("host", "127.0.0.1")
        udpsink.set_property("port", 5000)

        self.queueforstore = Gst.ElementFactory.make("queue", "storequeue")
        self.queueforstore.set_property("leaky", 1)

        udpsinkforstore = Gst.ElementFactory.make("udpsink", "storesink")
        udpsinkforstore.set_property("host", "localhost")
        udpsinkforstore.set_property("port", 9982)

        if (
            not self.pipe
            or not self.source
            or not inputCapsFilter
            or not videoconvert
            or not encoder
            or not rtph264pay
            or not self.teesplit
            or not self.queueforstream
            or not udpsink
            or not self.queueforstore
            or not udpsinkforstore
        ):
            print("ERROR: Not all elements could be created.")

        self.pipe.add(
            self.source,
            inputCapsFilter,
            videoconvert,
            encoder,
            rtph264pay,
            self.teesplit,
            self.queueforstream,
            udpsink,
            self.queueforstore,
            udpsinkforstore,
        )

        print("#--------------------------------------------------")

        # ret = self.source.link(inputCapsFilter)
        # print("source link inpurCapsFilters " + str(ret))
        # ret = inputCapsFilter.link(videoconvert)
        # print("inputCapsFilter link videoconvert " + str(ret))
        ret = self.source.link(inputCapsFilter)
        print("source link inpurCapsFilters " + str(ret))
        ret = inputCapsFilter.link(encoder)
        print("inputCapsFilter link encoder " + str(ret))
        ret = encoder.link(rtph264pay)
        print("encoder link rtph264pay " + str(ret))
        ret = rtph264pay.link(self.teesplit)
        print("rtph264pay link teesplit " + str(ret))

        print("#--------------------------------------------------")

        ret = self.queueforstream.link(udpsink)
        print("queueforstream link udpsink " + str(ret))

        print("#--------------------------------------------------")

        ret = self.queueforstore.link(udpsinkforstore)
        print("queueforstream link udpsink " + str(ret))

        print("#--------------------------------------------------")

        # manually link the tee, which has "Request" pads
        tee_src_pad_template = self.teesplit.get_pad_template("src_%u")
        teesplit_stream = self.teesplit.request_pad(tee_src_pad_template, None, None)
        print("Obtained request pad {0} for stream branch".format(teesplit_stream.get_name()))
        stream_queue_pad = self.queueforstream.get_static_pad("sink")
        ret = teesplit_stream.link(stream_queue_pad)
        print("teesplit link queueforstream " + "True" if ret == Gst.PadLinkReturn.OK else "False")

        teesplit_storefile = self.teesplit.request_pad(tee_src_pad_template, None, None)
        print("Obtained request pad {0} for storefile branch".format(teesplit_storefile.get_name()))
        storefile_queue_pad = self.queueforstore.get_static_pad("sink")
        try:
            ret = teesplit_storefile.link(storefile_queue_pad)
            print("teesplit link queueforstore " + "True" if ret == Gst.PadLinkReturn.OK else "False")
        except:
            print("teesplit link fs_queue Error")

        print("#--------------------------------------------------")

    def makeRaspiRecordPipeline(self):
        # Set up the gstreamer pipeline

        # recordPiplineStr = (
        #    "udpsrc name=recordsrc port=9982"
        #    + " ! application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96"
        #    + " ! queue name=recvqueue ! rtph264depay ! h264parse ! mp4mux"
        #    + " ! filesink name=filesink location=default.mp4 -e"
        # )

        # print(recordPiplineStr)
        # self.recordpipe = Gst.parse_launch(recordPiplineStr)

        self.recordpipe = Gst.Pipeline.new("StreamStore")
        # udpsrc recording
        # recordsource = Gst.ElementFactory.make("udpsrc", "recordsrc")
        # recordsource.set_property("port", 9982)

        # rtspsrc recording
        recordsource = Gst.ElementFactory.make("rtspsrc", "recordsrc")
        recordsource.set_property("location", ("rtsp://localhost:" + str(self.port) + "/" + self.streamName))

        capsString = "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96"
        inputCaps = Gst.Caps.from_string(capsString)
        inputCapsFilter = Gst.ElementFactory.make("capsfilter", "filter")
        inputCapsFilter.set_property("caps", inputCaps)

        recordrecvqueue = Gst.ElementFactory.make("queue", "recvqueue")

        recordrtph264depay = Gst.ElementFactory.make("rtph264depay", "rtph264depay")
        recordh264parse = Gst.ElementFactory.make("h264parse", "h264parse")

        recordmp4mux = Gst.ElementFactory.make("mp4mux", "mp4mux")
        recordfilesink = Gst.ElementFactory.make("filesink", "filesink")
        recordfilesink.set_property("location", "default.mp4")

        if (
            not self.recordpipe
            or not recordsource
            or not inputCapsFilter
            or not recordrecvqueue
            or not recordrtph264depay
            or not recordh264parse
            or not recordmp4mux
            or not recordfilesink
        ):
            print("ERROR: Not all elements could be created.")

        self.recordpipe.add(recordsource)
        self.recordpipe.add(inputCapsFilter)
        self.recordpipe.add(recordrecvqueue)
        self.recordpipe.add(recordrtph264depay)
        self.recordpipe.add(recordh264parse)
        self.recordpipe.add(recordmp4mux)
        self.recordpipe.add(recordfilesink)

        print("#--------------------------------------------------")

        ret = recordsource.link(inputCapsFilter)
        print("record source link inpurCapsFilters " + str(ret))
        ret = inputCapsFilter.link(recordrecvqueue)
        print("record source link recordrecvqueue " + str(ret))
        ret = recordrecvqueue.link(recordrtph264depay)
        print("recordrecvqueue link record rtph264depay " + str(ret))
        ret = recordrtph264depay.link(recordh264parse)
        print("record rtph264depay link record h264parse " + str(ret))

        ret = recordh264parse.link(recordmp4mux)
        print("record h264parse link recordmp4mux " + str(ret))
        ret = recordmp4mux.link(recordfilesink)
        print("record mp4mux link record filesink " + str(ret))

        print("#--------------------------------------------------")

    def makeRaspiPipeline(self):

        self.bitrate = "10000000"

        self.source = Gst.ElementFactory.make("rpicamsrc", "camsource")
        self.source.set_property("sensor-mode", "1920x1080")
        self.source.set_property("preview", "false")
        self.source.set_property("bitrate", self.bitrate)
        self.source.set_property("keyframe-interval=", "60")
        self.source.set_property("image-effect", "denoise")

        # self.source = Gst.ElementFactory.make("v4l2src", "camsource")
        # self.source.set_property("do-timestamp", "true")

        capsString = "video/x-h264,profile=baseline,width=1920,height=1080,framerate=30/1"
        inputCaps = Gst.Caps.from_string(capsString)
        inputCapsFilter = Gst.ElementFactory.make("capsfilter", "filter")
        inputCapsFilter.set_property("caps", inputCaps)

        h264parse = Gst.ElementFactory.make("h264parse", "h264parse")

        rtph264pay = Gst.ElementFactory.make("rtph264pay", "rtph264pay")
        rtph264pay.set_property("pt", 96)
        rtph264pay.set_property("config-interval", -1)
        rtph264pay.set_property("aggregate-mode", "zero-latency")

        self.teesplit = Gst.ElementFactory.make("tee", "teesplit")

        self.queueforstream = Gst.ElementFactory.make("queue", "vidqueue")
        self.queueforstream.set_property("leaky", 1)

        udpsink = Gst.ElementFactory.make("udpsink", "outsink")
        udpsink.set_property("host", "192.168.2.102")
        udpsink.set_property("port", 5000)

        self.queueforstore = Gst.ElementFactory.make("queue", "storequeue")
        # self.queueforstore.set_property("leaky", 1)

        udpsinkforstore = Gst.ElementFactory.make("udpsink", "storesink")
        udpsinkforstore.set_property("host", "127.0.0.1")
        udpsinkforstore.set_property("port", 9982)

        if (
            not self.pipe
            or not self.source
            or not inputCapsFilter
            or not h264parse
            or not rtph264pay
            or not self.teesplit
            or not self.queueforstream
            or not udpsink
            or not self.queueforstore
            or not udpsinkforstore
        ):
            print("ERROR: Not all elements could be created.")

        self.pipe.add(self.source)
        self.pipe.add(inputCapsFilter)
        self.pipe.add(h264parse)
        self.pipe.add(rtph264pay)
        self.pipe.add(self.teesplit)
        self.pipe.add(self.queueforstream)
        self.pipe.add(udpsink)
        self.pipe.add(self.queueforstore)
        self.pipe.add(udpsinkforstore)

        print("#--------------------------------------------------")

        ret = self.source.link(inputCapsFilter)
        print("source link inpurCapsFilters " + str(ret))
        ret = inputCapsFilter.link(h264parse)
        print("inputCapsFilter link h264parse " + str(ret))
        ret = h264parse.link(rtph264pay)
        print("h264parse link rtph264pay " + str(ret))
        ret = rtph264pay.link(self.teesplit)
        print("rtph264pay link teesplit " + str(ret))

        print("#--------------------------------------------------")

        ret = self.queueforstream.link(udpsink)
        print("queueforstream link udpsink " + str(ret))

        print("#--------------------------------------------------")

        ret = self.queueforstore.link(udpsinkforstore)
        print("queueforstore link udpsink " + str(ret))

        print("#--------------------------------------------------")

        # manually link the tee, which has "Request" pads
        tee_src_pad_template = self.teesplit.get_pad_template("src_%u")
        teesplit_stream = self.teesplit.request_pad(tee_src_pad_template, None, None)
        print("Obtained request pad {0} for stream branch".format(teesplit_stream.get_name()))
        stream_queue_pad = self.queueforstream.get_static_pad("sink")
        ret = teesplit_stream.link(stream_queue_pad)
        print("teesplit link queueforstream " + "True" if ret == Gst.PadLinkReturn.OK else "False")

        teesplit_storefile = self.teesplit.request_pad(tee_src_pad_template, None, None)
        print("Obtained request pad {0} for storefile branch".format(teesplit_storefile.get_name()))
        storefile_queue_pad = self.queueforstore.get_static_pad("sink")
        try:
            ret = teesplit_storefile.link(storefile_queue_pad)
            print("teesplit link queueforstore " + "True" if ret == Gst.PadLinkReturn.OK else "False")
        except:
            print("teesplit link fs_queue Error")

        print("#--------------------------------------------------")

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("Get EOS message")
            self.pipe.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
            self.pipe.set_state(Gst.State.NULL)

    def on_sync_message(self, bus, message):
        struct = message.get_structure()
        if not struct:
            return
        message_name = struct.get_name()
        if message_name == "prepare-xwindow-id":
            # Assign the viewport
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)

    def on_message_for_record(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("Record recv EOS message")
            # self.recordpipe.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Record Error: %s" % err, debug)
            self.recordpipe.set_state(Gst.State.NULL)

    def on_sync_message_for_record(self, bus, message):
        struct = message.get_structure()
        if not struct:
            return
        message_name = struct.get_name()
        if message_name == "prepare-xwindow-id":
            # Assign the viewport
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)

    def SetStreamInfo(self, width, height, fps, brightness, saturation, bitrate):
        # outsink = self.pipe.get_by_name('outsink')
        # outsink.set_property('host', targetip)
        # outsink.set_property('port', targetport)
        self.streamRTSPServer.setoptions(width, height, fps, brightness, saturation, bitrate)
        print(
            "SetStreamInfo width : "
            + str(width)
            + ", height : "
            + str(height)
            + ", fps : "
            + str(fps)
            + ", bitrate : "
            + str(bitrate)
        )

    def StreamingStart(self):
        if self.IsStreaming == True:
            return Error.Stream_Already_Running

        # start playing
        self.streamRTSPServer.launch()
        self.IsStreaming = True
        return Error.Success

    def StreamingStop(self):
        if self.IsStreaming == False:
            return Error.Stream_Not_Running

        if self.IsStoreFile == True:
            self.stopStroeFile()

        # stop playing
        self.streamRTSPServer.stop()
        self.IsStreaming = False

        self.killallprocessbyName("gst-launch-1.0")

        return Error.Success

    def CaptureLastImage(self):

        cmd = (
            "gst-launch-1.0 "
            + "rpicamsrc num-buffers=10 keyframe-interval=1"
            + " ! image/jpeg, framerate=30/1, width="
            + str(self.width)
            + ", height="
            + str(self.height)
            + " ! jpegparse ! filesink location=lastimage.jpg"
        )
        print(cmd)

        try:
            if not self.captureImageProcess:
                self.captureImageProcess.terminate()
        except:
            print("CaptureLastImage is not found")

        try:
            self.captureImageProcess = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
        except:
            print("CaptureLastImage run failed")
            return Error.Unknown

        return Error.Success

    def StoreFileStart(self, targetpathname, requestURL):
        if self.IsStreaming == False:
            return Error.Stream_Not_Running
        if self.IsStoreFile == True:
            return Error.Store_Already_Running
        self.recordpipe.set_state(Gst.State.NULL)

        # recordpipestr = (
        #    "rtspsrc location=rtsp://192.168.0.112:8554/raspiVideo latency=0"
        #    + " ! "
        #    + '"application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96"'
        #    + " ! queue ! rtph264depay ! h264parse ! mp4mux ! filesink location="
        #    + targetpathname
        # )
        # print(recordpipestr)
        # cmd = ["gst-launch-1.0", "-e", "-v", recordpipestr]

        cmd = (
            "gst-launch-1.0 -e -v "
            + "rtspsrc location="
            + requestURL
            + " latency=0"
            + ' ! "application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96"'
            + " ! queue ! rtph264depay ! h264parse ! mp4mux ! filesink location="
            + targetpathname
        )
        print(cmd)

        try:
            if not self.recordProcess:
                self.recordProcess.terminate()
        except:
            print("recordProcess is not found")

        try:
            self.recordProcess = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
        except:
            print("recordProcess run failed")
            self.IsStoreFile = False
            return Error.Store_Start_Failed

        self.IsStoreFile = True
        return Error.Success

        recordfilesink = self.recordpipe.get_by_name("filesink")
        recordfilesink.set_property("location", targetpathname)
        ret = self.recordpipe.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            self.IsStoreFile = False
            return Error.Store_Start_Failed

        self.IsStoreFile = True
        return Error.Success

    def killallprocessbyName(self, processName):
        processlist = subprocess.Popen(["ps", "-A"], stdout=subprocess.PIPE)
        output, error = processlist.communicate()
        # print(output)

        for line in output.splitlines():
            if processName in str(line):
                print(line)
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGTERM)

    def killprocessbyName(self, processName):
        processlist = subprocess.Popen(["ps", "-A"], stdout=subprocess.PIPE)
        output, error = processlist.communicate()
        # print(output)

        for line in output.splitlines():
            if processName in str(line):
                print(line)
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGINT)

    def stopStroeFile(self):
        if self.IsStoreFile == False:
            return Error.Store_Not_Running

        try:
            print("recordProcess " + str(self.recordProcess.pid))
            self.killprocessbyName("gst-launch-1.0")
        except:
            print("recordProcess kill error")

        self.IsStoreFile = False
        print("Stopped recording")
        return

        source = self.recordpipe.get_by_name("recordsrc")
        if source.send_event(Gst.Event.new_eos()):
            print("send Event EOS to source Success")

        h264parse = self.recordpipe.get_by_name("h264parse")
        if h264parse.send_event(Gst.Event.new_eos()):
            print("send Event EOS to h264parse Success")

        platformname = platform.system()
        if platformname == "Darwin":
            print("stop Store file platform Darwin")

            # mp4mux = self.recordpipe.get_by_name("mp4mux")
            # if (mp4mux.send_event(Gst.Event.new_eos())):
            #    print("send Event EOS to mp4mux Success")
            # filesink = self.recordpipe.get_by_name("filesink")
            # if (filesink.send_event(Gst.Event.new_eos())):
            #    print("send Event EOS to finlsink Success")
            # if (self.recordpipe.send_event(Gst.Event.new_eos())):
            #    print("send Event EOS to Send Record pipeline")
            return
        else:
            mp4mux = self.recordpipe.get_by_name("mp4mux")
            if mp4mux.send_event(Gst.Event.new_eos()):
                print("send Event EOS to mp4mux Success")
            filesink = self.recordpipe.get_by_name("filesink")
            if filesink.send_event(Gst.Event.new_eos()):
                print("send Event EOS to finlsink Success")
            if self.recordpipe.send_event(Gst.Event.new_eos()):
                print("send Event EOS to Send Record pipeline")

        # recordbus = self.recordpipe.get_bus()
        # recordbus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)

        # self.recordpipe.set_state(Gst.State.NULL)
        print("Stopped recording")

    def StoreFileStop(self):
        if self.IsStreaming == False:
            return Error.Stream_Not_Running

        self.stopStroeFile()

        self.IsStoreFile = False
        return Error.Success
