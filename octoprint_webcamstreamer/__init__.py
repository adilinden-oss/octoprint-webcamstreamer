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

class WebcamStreamerPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin):

    def __init__(self):
        self.client = docker.from_env()
        self.container = None
    
    ##~~ StartupPlugin
    
    def on_after_startup(self):
        self._logger.info("OctoPrint-WebcamStreamer loaded! Checking stream status.")
        try:
            self.container = self.client.containers.get('WebcamStreamer')
            self._logger.info("%s is streaming " % self.container.name)
            self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
        except Exception, e:
            self._logger.error(str(e))
            self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))

    ##~~ TemplatePlugin
    
    def get_template_configs(self):
        return [dict(type="settings",custom_bindings=False)]

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            channel_id="",
            stream_url="rtmp://a.rtmp.youtube.com/live2",
            stream_id="",
            webcam_url="",
            streaming=False,
            auto_start=False
        )

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
            self.startStream()

        if command == 'stopStream':
            self._logger.info("Stop stream command received.")
            self.stopStream()

        if command == 'checkStream':
            self._logger.info("Checking stream status.")
            if self.container:
                self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
            else:
                self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))

    ##-- EventHandlerPlugin
    
    def on_event(self, event, payload):
        if event == "PrintStarted" and self._settings.get(["auto_start"]):
            self.startStream()
            
        if event in ["PrintDone","PrintCancelled"] and self._settings.get(["auto_start"]):
            self.stopStream()

    ##-- Utility Functions
    
    def startStream(self):
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
            try:
                self.container = self.client.containers.run(
                    "adilinden/rpi-stream:latest",
                    command=[
                        "octopi-youtubelive",
                        self._settings.get(["webcam_url"]),
                        self._settings.get(["stream_url"]),
                        self._settings.get(["stream_id"]),
                        ",".join(filters)],
                        detach=True,
                        privileged=True,
                        name="WebcamStreamer",
                        auto_remove=True)
                self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
            except Exception, e:
                self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
        return
        
    def stopStream(self):
        if self.container:
            try:
                self.container.stop()
                self.container = None
                self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))
            except Exception, e:
                self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
        else:
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

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = WebcamStreamerPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

