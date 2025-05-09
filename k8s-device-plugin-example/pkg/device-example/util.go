package device_example

import (
	"k8s.io/klog/v2"
	pluginapi "k8s.io/kubelet/pkg/apis/deviceplugin/v1beta1"
)

const (
	resourceName = "huawei.com/Ascend910"
	serverSock   = pluginapi.DevicePluginPath + "deviceexample.sock"
)

func getDevices() []*pluginapi.Device {
	devs := []*pluginapi.Device{
		{ID: "Dev-1", Health: pluginapi.Healthy},
		{ID: "Dev-2", Health: pluginapi.Healthy},
	}

	klog.Info("devs: ", devs)

	return devs
}
