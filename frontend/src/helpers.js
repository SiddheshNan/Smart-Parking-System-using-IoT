export const WS_URL = "ws://localhost:8888/ws"

export const getUserTimeZone = () => {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
};

export const createLocalTimeFromEpoch = (time) => {
  if (!time) return "Never";

  return new Date(parseInt(time))
    .toLocaleString("en-IN", { timeZone: getUserTimeZone() })
    .toUpperCase();
};

export const createLocalTime = (time) => {
  if (!time) return "Never";

  return new Date(time)
    .toLocaleString("en-IN", { timeZone: getUserTimeZone() })
    .toUpperCase();
};
