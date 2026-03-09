import { LaunchSessionStore } from "./launchSessionStore";

const SHARED_LAUNCH_SESSION_STORE = new LaunchSessionStore();

export function getSharedLaunchSessionStore(): LaunchSessionStore {
    return SHARED_LAUNCH_SESSION_STORE;
}
