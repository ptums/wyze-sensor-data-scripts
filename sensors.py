import logging
import os
from wyze_sdk import Client
from pymongo import MongoClient
from dotenv import load_dotenv
# from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

email = os.getenv('email')
password = os.getenv('password')
keyid = os.getenv('keyid')
apiKey = os.getenv('apiKey')
accessToken = os.getenv('accessToken')
refreshToken = os.getenv('refreshToken')
db_url = os.getenv('db_url')
device_one = os.getenv('device_one')
device_two = os.getenv('device_two')
device_three = os.getenv('device_three')
device_four = os.getenv('device_four')

client_sm = Client(token=accessToken)
client_db = MongoClient(db_url)

db = client_db['smart_home']
collection = db['devices']


class Device:
    def __init__(self, mac="", nickname="", is_online="", product_model="", product_type=""):
        self.mac = mac
        self.nickname = nickname
        self.is_online = is_online
        self.product_model = product_model
        self.product_type = product_type

    def to_bson(self):
        return self.__dict__

    def __str__(self):
        return f"Device: (mac={self.mac}, nickname={self.nickname}), is_online={self.is_online} product_model={self.product_model} product_type={self.product_type}"


def store_device_details(device):
    result = collection.insert_one(device.__dict__)
    _LOGGER.info(f'Device inserted with ID: {result.inserted_id}')


def sync_devices():
    device_mac_list = [device_one, device_two, device_three, device_four]
    for device in client_sm.devices_list():
        if device.mac in device_mac_list:
            device_obj = Device(mac=device.mac, is_online=device.is_online, nickname=device.nickname, product_model=device.product.model, product_type=device.product.type)
            store_device_details(device=device_obj)
            _LOGGER.info(f'Synced device: {device_obj}')


def wyze_sdk_entry_sensor_details(device):
    mac = device['mac']
    product_type = device['product_type']
    name = device['nickname']
    data = {}
    if product_type == 'MotionSensor':
        motion_sensor_details = client_sm.motion_sensors.info(device_mac=mac)
        data = motion_sensor_details.to_dict()
    elif product_type == 'ContactSensor':
        contact_sensor_details = client_sm.entry_sensors.info(device_mac=mac)
        data = contact_sensor_details.to_dict()

    _LOGGER.info(f'Device: {name}, Data: {data}')
    return data


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Wyze sensor platform."""
    add_entities([WyzeSensor()])


class WyzeSensor(Entity):
    """Representation of a Wyze sensor."""

    def __init__(self):
        """Initialize the sensor."""
        self._state = None
        self._device_data = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Wyze Sensor'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._device_data

    def update(self):
        """Fetch new state data for the sensor."""
        collection_count = collection.estimated_document_count()
        if collection_count == 0:
            sync_devices()

        cursor = collection.find({})
        for document in cursor:
            self._device_data[document['nickname']] = wyze_sdk_entry_sensor_details(document)
            self._state = 'updated'

