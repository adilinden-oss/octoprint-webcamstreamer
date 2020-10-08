# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.server import user_permission
import docker

class WebcamStreamerPlugin(octoprint.plugin.StartupPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.SimpleApiPlugin,
                           octoprint.plugin.EventHandlerPlugin):

    def __init__(self):
        # Docker connection and container object
        self.client = None
        self.image = None
        self.container = None
    
        self.frame_rate_default = 5
        self.ffmpeg_cmd_default = (
            "ffmpeg -re -f mjpeg -framerate 5 -i {webcam_url} "                                                                   # Video input
            "-ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero "                                               # Audio input
            "-acodec aac -ab 128k "                                                                                        # Audio output
            "-vcodec h264 -pix_fmt yuv420p -framerate {frame_rate} -g {gop_size} -strict experimental -filter:v {filter} " # Video output
            "-f flv {stream_url}")                                                                                         # Output stream
        self.docker_image_default = "adilinden/rpi-ffmpeg:latest"
        self.docker_container_default = "WebStreamer"

    ##~~ StartupPlugin
    
    def on_after_startup(self):
        self._logger.info(
            "OctoPrint-WebcamStreamer loaded! \n"
            + "|  embed_url = " + self._settings.get(["embed_url"]) + "\n"
            + "|  stream_url = " + self._settings.get(["stream_url"]) + "\n"
            + "|  webcam_url = " + self._settings.get(["webcam_url"]) + "\n"
            + "|  docker_image = " + self._settings.get(["docker_image"]) + "\n"
            + "|  docker_container = " + self._settings.get(["docker_container"]) + "\n"
            + "|  frame_rate = " + str(self._settings.get(["frame_rate"])) + "\n"
            + "|  ffmpeg_cmd = " + self._settings.get(["ffmpeg_cmd"]))
        self._get_image()
        self._check_stream()

    ##~~ TemplatePlugin
    
    def get_template_configs(self):
        return [dict(type="settings",custom_bindings=False)]

    def get_template_vars(self):
        return dict(
            frame_rate_default = self.frame_rate_default,
            ffmpeg_cmd_default = self.ffmpeg_cmd_default,
            docker_image_default = self.docker_image_default,
            docker_container_default = self.docker_container_default
        )

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            embed_url = "",
            stream_url = "",
            webcam_url = "",
            streaming = False,
            auto_start = False,
            ffmpeg_cmd = self.ffmpeg_cmd_default,
            frame_rate = self.frame_rate_default,
            docker_image = self.docker_image_default,
            docker_container = self.docker_container_default,

            # Default values
            frame_rate_default = self.frame_rate_default,
            ffmpeg_cmd_default = self.ffmpeg_cmd_default,
            docker_image_default = self.docker_image_default,
            docker_container_default = self.docker_container_default
        )

    def get_settings_restricted_paths(self):
        return dict(admin=[["stream_url"]])

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/webcamstreamer.js"],
            css=["css/webcamstreamer.css"],
            less=["less/webcamstreamer.less"]
        )

    ##~~ SimpleApiPlugin
    
    def get_api_commands(self):
        return dict(startStream=[],stopStream=[],checkStream=[])
        
    def on_api_command(self, command, data):
        if not user_permission.can():
            from flask import make_response
            return make_response("Insufficient rights", 403)
        
        if command == 'startStream':
            self._logger.info("Start stream command received.")
            self._start_stream()

        if command == 'stopStream':
            self._logger.info("Stop stream command received.")
            self._stop_stream()

        if command == 'checkStream':
            self._logger.info("Checking stream status.")
            self._check_stream()

    ##-- EventHandlerPlugin
    
    def on_event(self, event, payload):
        if event == "PrintStarted" and self._settings.get(["auto_start"]):
            self._start_stream()
            
        if event in ["PrintDone","PrintCancelled"] and self._settings.get(["auto_start"]):
            self._stop_stream()

    ##-- Utility Functions

    def _get_client(self):
        self.client = docker.from_env()
        try:
            self.client.ping()
        except Exception as e:
            self._logger.error("Docker not responding: " + str(e))
            self.client = None

    def _get_image(self):
        self._get_client()
        if self.client:
            try:
                self.image = self.client.images.get(self._settings.get(["docker_image"]))
            except Exception as e:
                self._logger.error(str(e))
                self._logger.error("Please read installation instructions!")
                self.image = None

    def _get_container(self):
        self._get_client()
        if self.client:
            try:
                self.container = self.client.containers.get(self._settings.get(["docker_container"]))
            except Exception as e:
                self.client = None
                self.container = None
    
    def _start_stream(self):
        self._get_container()
        if not self.container:
            filters = []
            if self._settings.global_get(["webcam","flipH"]):
                filters.append("hflip")
            if self._settings.global_get(["webcam","flipV"]):
                filters.append("vflip")
            if self._settings.global_get(["webcam","rotate90"]):
                filters.append("transpose=cclock")
            if len(filters) == 0:
                filters.append("null")
            gop_size = int(self._settings.get(["frame_rate"])) * 2
            # Substitute vars in ffmpeg command
            docker_cmd = self._settings.get(["ffmpeg_cmd"]).format(
                webcam_url = self._settings.get(["webcam_url"]),
                stream_url = self._settings.get(["stream_url"]),
                frame_rate = self._settings.get(["frame_rate"]),
                gop_size = gop_size,
                filter = ",".join(filters))
            self._logger.info("Launching docker container '" + self._settings.get(["docker_container"]) + "':\n" + "|  " + docker_cmd)
            try:
                self._get_client()
                self.container = self.client.containers.run(
                    self._settings.get(["docker_image"]),
                    command = docker_cmd,
                    detach = True,
                    privileged = False,
                    devices = ["/dev/vchiq"],
                    name = self._settings.get(["docker_container"]),
                    auto_remove = True,
					network_mode = "host")
            except Exception as e:
                self._logger.error(str(e))
                self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
            else:
                self._logger.info("Stream started successfully")
                self._plugin_manager.send_plugin_message(self._identifier, dict(success="Stream started",status=True,streaming=True))
        return
        
    def _stop_stream(self):
        self._get_container()
        if self.container:
            try:
                self.container.stop()
                self.container = None
            except Exception as e:
                self._logger.error(str(e))
                self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
            else:
                self._logger.info("Stream stopped successfully")
                self._plugin_manager.send_plugin_message(self._identifier, dict(success="Stream stopped",status=True,streaming=False))
        else:
            self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))

    def _check_stream(self):
        self._get_container()
        if self.container:
            self._logger.info("%s is streaming " % self.container.name)
            self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
        else:
            self._logger.info("stream is inactive ")
            self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            webcamstreamer=dict(
                displayName="WebcamStreamer Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="adilinden-oss",
                repo="octoprint-webcamstreamer",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/adilinden-oss/octoprint-webcamstreamer/archive/{target_version}.zip"
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "WebcamStreamer Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = WebcamStreamerPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

