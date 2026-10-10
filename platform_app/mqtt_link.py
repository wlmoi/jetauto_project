import logging
import ssl

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


def make_client(client_id, config):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=True)
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
    if config.mqtt_tls:
        client.tls_set(ca_certs=config.mqtt_ca or None, cert_reqs=ssl.CERT_REQUIRED)
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    client.max_queued_messages_set(20)
    return client
