import atexit
import sys
import logging
import time
import getpass
import psutil
import random
import uuid
import platform

from sh import scutil, ifconfig, networksetup


class WIFIonICE:

    TRAFFIC_LIMIT = 180
    WIFI_SSID = "WIFIonICE"

    def __init__(self):
        self.logger = logging.getLogger(self.WIFI_SSID)
        self.init_usage = self.traffic_usage()

        self.original_hostname = self.get_hostname()

        if self.init_usage >= self.TRAFFIC_LIMIT:
            self.logger.info("Initial reconnect because the script don't know if the limit has been already exeeded.")
            self.reconnect()

        self.run()

    def handle_exit(self):
        self.logger.info("Exiting, restoring original hostname")
        self.set_hostname(self.original_hostname)

    def traffic_usage(self):
        """
        Returns the current traffic usage from the network interfaces in MB
        :return: int
        """
        psutil.net_io_counters()

        sent = int(psutil.net_io_counters().bytes_sent) / 1000000
        received = int(psutil.net_io_counters().bytes_recv) / 1000000

        return round(sent + received)

    def reconnect(self):
        """
        Reconnects the WIFI connection with new MAC address and hostname
        """
        networksetup("-removepreferredwirelessnetwork", "en0", self.WIFI_SSID)

        self.set_hostname(self.generate_new_hostname())

        ifconfig("en0", "ether", self.generate_new_mac())

        networksetup("-setairportnetwork", "en0", self.WIFI_SSID)
        self.init_usage = self.traffic_usage()

    def generate_new_mac(self):
        """
        Generates a random valid MAC address
        :return: string
        """
        mac = [ 0x00, 0x16, 0x3e,
                random.randint(0x00, 0x7f),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff) ]

        return ':'.join(map(lambda x: "%02x" % x, mac))

    def generate_new_hostname(self):
        """
        Generates a random hostname
        :return: string
        """
        random_string = str(uuid.uuid4())
        random_string = random_string.upper()
        random_string = random_string.replace("-", "")

        return random_string[0:10]

    def set_hostname(self, hostname):
        scutil("--set", "HostName", hostname)

    def get_hostname(self):
        return scutil("--get", "HostName")

    def run(self):
        self.logger.info("Starting WIFIonICE Daemon")

        while True:
            traffic_usage = self.traffic_usage() - self.init_usage

            self.logger.info("Checking Traffic Usage, {used}/{available} MB traffic used".format(
                used=traffic_usage,
                available=self.TRAFFIC_LIMIT
            ))

            if traffic_usage >= self.TRAFFIC_LIMIT:
                self.logger.info("Traffic Usage exeeded. Reconnecting now...")
                self.reconnect()

            time.sleep(5)


if __name__ == '__main__':
    # Command line stub for debugging. You can directly call this script for
    # debugging purposes. Always sets the DEBUG log level and does not write
    # to a log file.

    logging.basicConfig(
        stream=sys.stdout,
        format="%(levelname)s - %(name)s -> %(message)s",
        level=logging.INFO)

    if not platform.system() == 'Darwin':
        print("This script does only support Mac OS X right now.")
        sys.exit(1)

    if not getpass.getuser() == 'root':
        print("Please run this script as root.")
        sys.exit(1)

    ice = WIFIonICE()
    atexit.register(lambda x: ice.handle_exit())
