from pywebpush import webpush
import json
import logging
import datetime


def send_push_notification(subscription, payload):

    try:

        # subscriptionData = json.loads(subscription)

        # logger.error(subscriptionData)

        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": subscription["keys"],
            },
            data=json.dumps(payload),
            vapid_claims={
                "aud": "https://eshopper.africa",
                "exp": int((datetime.datetime.now().timestamp())) + 86400,
                "sub": "mailto:events@eshopper.africa",
            },
            vapid_private_key="UCUKEHn7Jd33QZx5lJFKBY4plOxGsJ6xJSOzE14jQlo",
        )

        # subscription_info = { 'endpoint': subscription['endpoint'], 'keys': subscription['keys'] },

        # data = json.loads(payload),

        # headers = {}

        # ttl = 0

        # gcm_key = ''

        # content_encoding="aes128gcm"

        # reg_id=""

        # WebPusher = webpush(subscription_info)

        # WebPusher(subscription_info).send(data, headers, ttl, gcm_key, reg_id, content_encoding, timeout=None)

    except Exception as inst:
        print(f" webpush Notification Error : {inst}")


send_push_notification({"endpoint": "https://example.com", "keys": {}}, "laaaa")
