"""User-Agent detection service for identifying request origins."""
import logging

from flask import request

logger = logging.getLogger(__name__)


class UserAgentDetector:
    """Detect and analyse User-Agent strings."""

    CORDOVA_INDICATORS = [
        "cordova",
        "capacitor",
        # 'wv' indicates an Android WebView (present in Chrome WebView user-agent strings)
        " wv)",
        "android webview",
    ]

    BOT_INDICATORS = [
        "bot",
        "crawler",
        "spider",
        "scraper",
    ]

    @staticmethod
    def get_user_agent() -> str:
        """Return the User-Agent header from the current request."""
        return request.headers.get("User-Agent", "Unknown")

    @staticmethod
    def is_cordova() -> bool:
        """Return True if the request appears to originate from a Cordova/WebView environment."""
        user_agent = UserAgentDetector.get_user_agent().lower()
        return any(indicator in user_agent for indicator in UserAgentDetector.CORDOVA_INDICATORS)

    @staticmethod
    def is_bot() -> bool:
        """Return True if the request appears to originate from a bot or crawler."""
        user_agent = UserAgentDetector.get_user_agent().lower()
        return any(indicator in user_agent for indicator in UserAgentDetector.BOT_INDICATORS)

    @staticmethod
    def is_mobile_browser() -> bool:
        """Return True if the request appears to originate from a mobile browser."""
        user_agent = UserAgentDetector.get_user_agent().lower()
        mobile_indicators = ["mobile", "android", "iphone", "ipad", "windows phone"]
        return any(indicator in user_agent for indicator in mobile_indicators)

    @staticmethod
    def log_user_agent() -> None:
        """Log User-Agent diagnostic information for the current request."""
        logger.info("User-Agent: %s", UserAgentDetector.get_user_agent())
        logger.info("Is Cordova: %s", UserAgentDetector.is_cordova())
        logger.info("Is Mobile: %s", UserAgentDetector.is_mobile_browser())
        logger.info("Is Bot: %s", UserAgentDetector.is_bot())
