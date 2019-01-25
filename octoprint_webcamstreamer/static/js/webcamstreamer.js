/*
 * View model for OctoPrint-WebcamStreamer
 *
 * Author: Adi Linden
 * License: AGPLv3
 */
$(function () {
    function WebcamStreamerViewModel(parameters) {
        var self = this;
        
        self.settingsViewModel = parameters[0];
        self.is_configured = ko.observable();
        self.embed_url = ko.observable();
        self.streaming = ko.observable();
        self.processing = ko.observable(false);
        self.icon = ko.pureComputed(function() {
            var icons = [];
            if (self.streaming() && !self.processing()) {
                icons.push('icon-stop');
            } 
            
            if (!self.streaming() && !self.processing()){
                icons.push('icon-play');
            }
            
            if (self.processing()) {
                icons.push('icon-spin icon-spinner');
            } 
            
            return icons.join(' ');
        });
        self.btnclass = ko.pureComputed(function() {
            return self.streaming() ? 'btn-primary' : 'btn-danger';
        });
                                    

        // This will get called before the WebcamStreamerViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function () {
            if(self.settingsViewModel.settings.plugins.webcamstreamer.embed_url() &&
                    self.settingsViewModel.settings.plugins.webcamstreamer.embed_url() &&
                    self.settingsViewModel.settings.plugins.webcamstreamer.webcam_url()) {
                self.is_configured(true);
            } else {
                self.is_configured(false);
            }
            self.embed_url(self.settingsViewModel.settings.plugins.webcamstreamer.embed_url());
        };

        self.onEventSettingsUpdated = function (payload) {            
            if(self.settingsViewModel.settings.plugins.webcamstreamer.embed_url() &&
                    self.settingsViewModel.settings.plugins.webcamstreamer.embed_url() &&
                    self.settingsViewModel.settings.plugins.webcamstreamer.webcam_url()) {
                self.is_configured(true);
            } else {
                self.is_configured(false);
            }
            self.embed_url(self.settingsViewModel.settings.plugins.webcamstreamer.embed_url());
        };
        
        self.onAfterBinding = function() {
            $.ajax({
                    url: API_BASEURL + "plugin/webcamstreamer",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "checkStream"
                    }),
                    contentType: "application/json; charset=UTF-8"
                })
        }
        
        self.onTabChange = function(next, current) {
            if(next == '#tab_plugin_webcamstreamer'){
                if(self.settingsViewModel.settings.webcam.streamRatio() == '4:3'){
                    $('#webcamstreamer_wrapper').css('padding-bottom','75%');
                }
                self.embed_url(self.settingsViewModel.settings.plugins.webcamstreamer.embed_url());
            } else {
                self.embed_url('');
            }
        }
        
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "webcamstreamer") {
                return;
            }
            
            if(data.error) {
                new PNotify({
                    title: 'WebcamStreamer Error',
                    text: data.error,
                    type: 'error',
                    hide: false,
                    buttons: {
                        closer: true,
                        sticker: false
                    }
                });
            }

            if(data.success) {
                new PNotify({
                    title: 'WebcamStreamer',
                    text: data.success,
                    type: 'success',
                    hide: true,
                    delay: 6000,
                    buttons: {
                        closer: true,
                        sticker: false
                    }
                });
            }
            
            if(data.status) {
                if(data.streaming == true) {
                    self.streaming(true);
                } else {
                    self.streaming(false);
                }
                
            }
            
            self.processing(false);
        };
        
        self.toggleStream = function() {
            self.processing(true);
            if (self.streaming()) {
                $.ajax({
                    url: API_BASEURL + "plugin/webcamstreamer",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "stopStream"
                    }),
                    contentType: "application/json; charset=UTF-8"
                })
            } else {
                $.ajax({
                    url: API_BASEURL + "plugin/webcamstreamer",
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "startStream"
                    }),
                    contentType: "application/json; charset=UTF-8"
                })
            }
        }
    }

    // This is how our plugin registers itself with the application, by adding some configuration information to
    // the global variable ADDITIONAL_VIEWMODELS
    ADDITIONAL_VIEWMODELS.push([
            // This is the constructor to call for instantiating the plugin
            WebcamStreamerViewModel,

            // This is a list of dependencies to inject into the plugin, the order which you request here is the order
            // in which the dependencies will be injected into your view model upon instantiation via the parameters
            // argument
            ["settingsViewModel"],

            // Finally, this is the list of all elements we want this view model to be bound to.
            [("#tab_plugin_webcamstreamer")]
        ]);
});