from traceback import format_exc
from exopy.instruments.api import BaseStarter


class PythonStarter(BaseStarter):
    """Starter for legacy instruments.
    """

    def start(self, driver_cls, connection, settings):
        """Start the driver by first formatting the connections infos.
        """
        c = self.format_connection_infos(connection)
        c.update(settings)
        return driver_cls(c)

    def check_infos(self, driver_cls, connection, settings):
        """Attempt to open the connection to the instrument.
        """
        c = self.format_connection_infos(connection)
        # c.update(settings)
        driver = None
        try:
            driver = driver_cls(c)
            driver.connect()
            res = driver.connected
        except Exception:
            return False, format_exc()
        finally:
            if driver is not None:
                driver.close_connection()
        return res, ('Instrument does not appear to be connected but no '
                     'exception was raised.')

    def reset(self, driver):
        """Clear the driver cache.
        """
        driver.clear_cache()

    def stop(self, driver):
        """Close the connection.
        """
        driver.close_connection()

    def format_connection_infos(self, infos):
        """Format the connection to match the expectancy of the driver.
        """
        return infos
