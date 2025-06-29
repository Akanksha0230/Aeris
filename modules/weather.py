import requests
from langchain_groq import ChatGroq
from modules.utils import weather_description_fetcher
from logger import CustomLogger
from modules.utils import extract_location
import re

class WeatherModule:
    """
    Handles weather-related functionality, including fetching weather details for a given location.
    """

    def __init__(self, api_key):
        """
        Initialize the Weather Module.
        """

        self.llm = ChatGroq(
            api_key=api_key,
            model="llama3-8b-8192",
            temperature=0.7
        )
        # Initialize logger
        self.logger = CustomLogger().get_logger()
        self.logger.info("WeatherModule initialized.")
    
       


    @staticmethod
    def weather_description_fetcher(code):
        weather_conditions = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle",
            53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
            63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow",
            73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
            81: "Moderate rain showers", 82: "Heavy rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail"
        }
        return weather_conditions.get(code, "Unknown conditions")
    
    
    def fetch_weather(self, location, is_tomorrow=False):
        """
        Fetches the weather details for a given location using the Open-Meteo API.
        :param location: Location for which weather needs to be fetched.
        :return: Weather details or an error message.
        """
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}"

        try:
            # Fetch latitude and longitude
            geocode_response = requests.get(geocode_url)
            geocode_response.raise_for_status()
            geocode_data = geocode_response.json()

            if "results" not in geocode_data or len(geocode_data["results"]) == 0:
                CustomLogger().get_logger().warning(f"No weather details found for location: {location}")
                return f"Sorry, I couldn't find weather details for '{location}'. Please try the same or another location."

            latitude = geocode_data["results"][0]["latitude"]
            longitude = geocode_data["results"][0]["longitude"]
            location_name = geocode_data["results"][0]["name"]

            if is_tomorrow:
              weather_url = (
                  f"https://api.open-meteo.com/v1/forecast?"
                  f"latitude={latitude}&longitude={longitude}"
                  f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
                  f"&timezone=auto"
              )
            else:
                weather_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={latitude}&longitude={longitude}&current_weather=true"
                )
            
            # Fetch weather details
            # weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            if is_tomorrow:
                try:
                    daily = weather_data["daily"]
                    weather_code = daily["weathercode"][1]
                    temp_max = daily["temperature_2m_max"][1]
                    temp_min = daily["temperature_2m_min"][1]

                    description = weather_description_fetcher(weather_code)

                    message = (
                        f"The weather in {location_name} tomorrow will be {description}, "
                        f"with a high of {temp_max}°C and a low of {temp_min}°C."
                    )
                    CustomLogger().get_logger().info(f"Tomorrow's forecast for {location_name}: {message}")
                    return message
                except Exception as e:
                    CustomLogger().get_logger().error(f"Error parsing tomorrow's forecast for {location}: {e}")
                    return "Sorry, I couldn't fetch tomorrow’s forecast right now."

            else:
                if "current_weather" in weather_data:
                    current_weather = weather_data["current_weather"]
                    temperature = current_weather["temperature"]
                    windspeed = current_weather["windspeed"]
                    weather_code = current_weather.get("weathercode", -1)

                    weather_description = weather_description_fetcher(weather_code)

                    temperature_description = (
                        "hot" if temperature > 30 else "cold" if temperature < 15 else "moderate"
                    )

                    weather_message = (f"The current weather in {location_name} is {weather_description} with a temperature of "
                                       f"{temperature}°C ({temperature_description}) and a windspeed of {windspeed} km/h.")
                    CustomLogger().get_logger().info(f"Weather fetched successfully for {location_name}: {weather_message}")
                    return weather_message
                else:
                    CustomLogger().get_logger().warning(f"Weather details not available for {location}.")
                    return "Sorry, I couldn't fetch the weather details at this time."

        except requests.exceptions.RequestException as e:
            CustomLogger().get_logger().error(f"Error fetching weather data for {location}: {e}")
            return f"An error occurred while fetching weather data: {e}"

    import re

    

    def handle_weather(self, user_input):
        """
        Handles weather-related queries interactively with the user.
        :param user_input: The location or command related to weather.
        :return: Response message or weather details.
        """
        self.logger.info(f"Handling weather query: {user_input}")

        _, is_tomorrow = parse_weather_input(user_input)
        self.logger.info(f"Parsed location: {is_tomorrow}, Is tomorrow: {is_tomorrow}")

        
        # Extract location from the input
        # location = extract_location(user_input, self.llm)
        # self.logger.info(f"Extracted location: {location}")
        # # Fetch weather for the extracted location
        # response = self.fetch_weather(location,is_tomorrow)
        # self.logger.info(f"Weather response: {response}")
        # return response

        # Step 2: Extract raw location using LLM
        raw_location = extract_location(user_input, self.llm)
        self.logger.info(f"LLM-extracted location: {raw_location}")

        # Step 3: Clean up the extracted location
        # Strip unwanted keywords like 'what', 'is', 'the', 'weather', 'of', etc.
        location = raw_location.lower()
        for keyword in ["weather", "forecast", "tomorrow", "today", "is it", "will it", "rain", "sunny", "in", "be", "outside", "what", "is", "the", "of"]:
            location = location.replace(keyword, "")
        location = location.strip().title()

        self.logger.info(f"Sanitized location: {location}")

        # Step 4: Check for valid location
        if not location:
           msg = "Sorry, I couldn't identify the location. Could you rephrase your query?"
           self.logger.warning(msg)
           return msg

        # Step 5: Fetch and return weather
        try:
           response = self.fetch_weather(location, is_tomorrow)
           self.logger.info(f"Weather response: {response}")
           return response
        except Exception as e:
           self.logger.error(f"Error while fetching weather: {e}")
           return "An error occurred while fetching the weather. Please try again later."
def parse_weather_input(user_input):
        """
        Parses user input to extract the location and whether the user is asking about tomorrow's forecast.
        :param user_input: Natural language input like "Will it rain in Pune tomorrow?"
        :return: (location, is_tomorrow) — e.g., ("Pune", True)
        """
        user_input = user_input.lower()
        is_tomorrow = "tomorrow" in user_input or "next day" in user_input
    
        # Try to extract location after keywords like "in"
        match = re.search(r"in ([a-zA-Z\s]+)", user_input)
        if match:
            location = match.group(1)
        else:
            # Fallback: remove common weather-related words and assume rest is location
            location = user_input
    
        # Remove non-location words to isolate just the city/place name
            for keyword in [
                "weather", "forecast", "tomorrow", "today", "is it", "will it",
                "rain", "raining", "sunny", "snow", "cold", "hot", "outside", "be", "in", "the"
            ]:
               location = location.replace(keyword, "")
    
            location = location.strip().title()
        return location, is_tomorrow




