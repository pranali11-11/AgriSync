const SATARA_COORDINATES = { latitude: 17.6805, longitude: 74.0183 };

export async function fetchWeather(latitude, longitude) {
  const coordinates =
    latitude != null && longitude != null
      ? { latitude, longitude }
      : SATARA_COORDINATES;
  const params = new URLSearchParams({
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
    current: "temperature_2m,weather_code",
    daily: "precipitation_probability_max",
    forecast_days: "1",
    timezone: "auto",
  });
  const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
  if (!response.ok) throw new Error("Weather service unavailable");
  const data = await response.json();
  return {
    temperature: Math.round(data.current?.temperature_2m ?? 0),
    rainChance: data.daily?.precipitation_probability_max?.[0] ?? 0,
    weatherCode: data.current?.weather_code ?? 0,
  };
}
