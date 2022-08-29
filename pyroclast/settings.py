from functools import wraps
import os


SETTINGS_KEY = "configured"


def configure(f):
    """
    Force the API to set defaults if no user settings have been provided.
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.settings.get(SETTINGS_KEY, False):
            self.configure()

        return f(self, *args, **kwargs)

    return wrapper


class Settings:
    """
    Control the management and lifecycle of any Pyroclast API settings.
    """

    settings = {SETTINGS_KEY: False}

    def configure(self, **kwargs):
        """
        Configure the Pyroclast API for settings like backend URLs.

        By doing so, the Pyroclast API allows users to instantiate clients on
        demand without requiring the user to pass around settings.
        """
        # Schedule Settings.
        nomad_host = kwargs.pop("nomad_host", "127.0.0.1")
        if not nomad_host.startswith("http"):
            nomad_host = f"http://{nomad_host}"

        nomad_port = int(kwargs.pop("nomad_port", "4646"))

        os.environ["NOMAD_ADDR"] = f"{nomad_host}:{nomad_port}"

        # Generic Settings.
        Settings.settings.update(kwargs)
        Settings.settings[SETTINGS_KEY] = True
