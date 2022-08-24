
import sys
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject, GLib

loop = GLib.MainLoop()
Gst.init(None)

class MyFactory(GstRtspServer.RTSPMediaFactory):
	def __init__(self):
		GstRtspServer.RTSPMediaFactory.__init__(self)

	def do_create_element(self, url):
		#
		s_src = "v4l2src ! video/x-raw,width=1280,height=720,framerate=30/1"
		s_h264 = "omxh264enc ! video/x-h264, profile=baseline,bitrate=20000000"
		pipeline_str = "( {s_src} ! queue max-size-buffers=1 name=q_enc ! {s_h264} ! rtph264pay name=pay0 pt=96 )".format(**locals())

		# delay 3~4 sec, 15 fps
		#s_src = "v4l2src ! video/x-h264,framerate=30/1,width=1920,height=1080 ! h264parse ! decodebin" 
		#s_h264 = "omxh264enc ! video/x-h264, profile=baseline, bitrate=8000000"
		#pipeline_str = "( {s_src} ! queue max-size-buffers=1 name=q_enc ! {s_h264} ! rtph264pay name=pay0 pt=96 )".format(**locals())

		# for darwin
		#s_src = "avfvideosrc ! video/x-raw,rate=30,width=1280,height=720 ! videoconvert ! video/x-raw,format=I420"
		#s_h264 = "x264enc tune=zerolatency"
		#pipeline_str = "( {s_src} ! queue max-size-buffers=1 name=q_enc ! {s_h264} ! rtph264pay name=pay0 pt=96 )".format(**locals())

		# for raspi
		#s_src = "v4l2src do-timestamp=true ! video/x-h264,width=1920,height=1080,framerate=30/1"
		#s_h264 = "h264parse"
		#pipeline_str = "( {s_src} ! queue max-size-buffers=1 name=q_enc ! {s_h264} ! rtph264pay name=pay0 pt=96 )".format(**locals())
		#pipeline_str = "( v4l2src do-timestamp=true ! video/x-h264,width=1920,height=1080,framerate=30/1 ! h264parse ! rtph264pay pt=96 config-interval=1 )"
		#if len(sys.argv) > 1:
		#	pipeline_str = "".join(sys.argv[1:])
		print(pipeline_str)
		return Gst.parse_launch(pipeline_str)

class GstServer():
	def __init__(self):
		self.server = GstRtspServer.RTSPServer()
		print("after RTSPServer")
		f = MyFactory()
		print("MyFactory")
		f.set_shared(True)
		print("set_shared")
		m = self.server.get_mount_points()
		print("get_mount_points")
		m.add_factory("/test", f)
		print("add_factory")
		self.server.attach(None)
		print("attach")


		self.server.remove()

if __name__ == '__main__':
	s = GstServer()
	loop.run()