export const WS_URL = "ws://10.0.0.122:8888/ws"

export const getUserTimeZone = () => {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
};

export const createLocalTimeFromEpoch = (time) => {
  if (!time) return "Never";

  return new Date(parseInt(time)*1000)
    .toLocaleString("en-IN", { timeZone: getUserTimeZone() })
    .toUpperCase();
};

export const createLocalTime = (time) => {
  if (!time) return "Never";

  return new Date(time)
    .toLocaleString("en-IN", { timeZone: getUserTimeZone() })
    .toUpperCase();
};

export  const USERNAME = "admin"
export  const PASSWORD = "admin"