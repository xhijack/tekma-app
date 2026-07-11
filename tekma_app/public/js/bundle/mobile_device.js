let cached_mobile_device;

export function is_mobile_device() {
	if (cached_mobile_device !== undefined) {
		return cached_mobile_device;
	}

	if (typeof navigator === "undefined") {
		cached_mobile_device = false;
		return cached_mobile_device;
	}

	if (typeof navigator.userAgentData?.mobile === "boolean") {
		cached_mobile_device = navigator.userAgentData.mobile;
		return cached_mobile_device;
	}

	const user_agent =
		navigator.userAgent ||
		navigator.vendor ||
		"";

	const mobile_phone =
		/Android.*Mobile|iPhone|iPod|webOS|BlackBerry|IEMobile|Opera Mini|Windows Phone/i.test(
			user_agent
		);

	const android_tablet =
		/Android/i.test(user_agent) &&
		!/Mobile/i.test(user_agent);

	const ipad =
		/iPad/i.test(user_agent) ||
		(
			navigator.platform === "MacIntel" &&
			navigator.maxTouchPoints > 1
		);

	cached_mobile_device =
		mobile_phone ||
		android_tablet ||
		ipad;

	return cached_mobile_device;
}