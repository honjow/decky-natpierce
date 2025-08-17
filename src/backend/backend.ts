import { callable } from "@decky/api";
import { Config, ResourceType } from ".";

export const getCoreStatus = callable<[], boolean>("get_core_status");
export const setCoreStatus = callable<[boolean], [boolean, string]>("set_core_status");
export const restartCore = callable<[], boolean>("restart_core");

export const getConfig = callable<[], Config>("get_config");
export const getConfigValue = callable<[string], any>("get_config_value");
export const setConfigValue = callable<[string, any], []>("set_config_value");

export const checkUpdate = callable<[], []>("check_update");
export const upgrade = callable<[ResourceType, string | undefined], [boolean, string]>("upgrade");
export const cancelUpgrade = callable<[ResourceType], []>("cancel_upgrade");
export const getVersion = callable<[ResourceType], string>("get_version");
export const getLatestVersion = callable<[ResourceType], string>("get_latest_version");
export const isUpgrading = callable<[ResourceType], boolean>("is_upgrading");

export const getIP = callable<[], string>("get_ip");
