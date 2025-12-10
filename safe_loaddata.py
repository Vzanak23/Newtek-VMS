import os
import django
import json
from django.apps import apps
from django.core.serializers.json import DeserializationError
from django.db import IntegrityError, transaction

# Setup Django environment
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "varient_management.settings"
)  # <- Change this
django.setup()

json_file = "data_utf8.json"  # Your cleaned UTF-8 JSON file

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

success = 0
fail = 0

for obj in data:
    try:
        model_label = obj["model"]
        Model = apps.get_model(*model_label.split("."))
        fields = obj["fields"]
        pk = obj.get("pk")

        # Create instance manually
        instance = Model(**fields)
        if pk:
            instance.pk = pk

        with transaction.atomic():
            instance.save()
        success += 1

    except (IntegrityError, DeserializationError, Exception):
        fail += 1
