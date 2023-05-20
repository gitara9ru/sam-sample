import datetime
from decimal import Decimal
import json


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return int(obj)
        return json.JSONEncoder.default(self, obj)
