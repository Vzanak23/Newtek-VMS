# serializers.py
from rest_framework import serializers
from .models import *


class VarientAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = answer_tbl
        fields = "__all__"


class BoundingBoxCDSerializer(serializers.ModelSerializer):
    class Meta:
        model = boundingbox_cd_tbl
        fields = "__all__"


class VarientBoundingBoxSerializer(serializers.ModelSerializer):
    class Meta:
        model = boundingbox_tbl
        fields = "__all__"

class VarientBoundingBoxCDSerializer(serializers.ModelSerializer):
    class Meta:
        model = boundingbox_cd_tbl
        fields = "__all__"


class CharactersSerializer(serializers.ModelSerializer):
    class Meta:
        model = characters_tbl
        fields = "__all__"


class CheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = checkpoint_tbl
        fields = "__all__"


class ColorCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = color_code_tbl
        fields = "__all__"


class ConcernSerializer(serializers.ModelSerializer):
    class Meta:
        model = concern_tbl
        fields = "__all__"


class DeleteTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = delete_tbl
        fields = "__all__"


class FuelCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantFuelCharacter
        fields = "__all__"


class ImageProcessingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image_Processing
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = location_tbl
        fields = "__all__"


class ModelCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = model_checkpoint_tbl
        fields = "__all__"


class ModelCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = model_code_tbl
        fields = "__all__"


class MSTComCSSerializer(serializers.ModelSerializer):
    class Meta:
        model = mst_com_cs_tbl
        fields = "__all__"


class MSTSettableFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = mst_settableFields_tbl
        fields = "__all__"


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation_tbl
        fields = "__all__"


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = part_tbl
        fields = "__all__"


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = platform
        fields = "__all__"


class PolygonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Polygon
        fields = "__all__"


class VinReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = vin_report_tbl
        fields = "__all__"


class UserTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_tbl
        fields = "__all__"


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Custom_user
        fields = "__all__"


class AnswerSerializer(serializers.Serializer):
    qr_code = serializers.CharField()
    vin = serializers.CharField(allow_blank=True, required=False)
    model_code = serializers.CharField()
    part_no = serializers.CharField()
    part_name = serializers.CharField()
    answer = serializers.CharField()
    checkpoint = serializers.CharField()
    location = serializers.CharField()
    severity = serializers.CharField()
    attribute = serializers.CharField()
    highlight = serializers.CharField()
    concern = serializers.CharField()
    ocr_operation = serializers.CharField()
    actual_text = serializers.CharField()
    ocr_text = serializers.CharField()
    remark_image = serializers.CharField(
        allow_blank=True, required=False
    )
    vehicle_platform = serializers.CharField()
    emp_token = serializers.CharField()
    operator = serializers.CharField()
    log_date = serializers.DateTimeField()
    shift_name = serializers.CharField()
    image_path = serializers.CharField()
    qc_no = serializers.IntegerField()
    part_time = serializers.CharField()
    image_processing_type = serializers.CharField()


class BodyshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = bodyshop_tbl
        fields = "__all__"


class CharactersSerializer(serializers.ModelSerializer):
    class Meta:
        model = characters_tbl
        fields = "__all__"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Convert Boolean to 0 or 1
        rep["is_alphabet"] = 1 if instance.is_alphabet else 0
        rep["is_number"] = 1 if instance.is_number else 0
        return rep


class VarientColorCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = color_code_tbl
        fields = [
            "id",
            "color_code",
            "color_name",
            "r_from",
            "g_from",
            "b_from",
            "r_to",
            "g_to",
            "b_to",
            "log_date",
        ]


class VarientFuelCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantFuelCharacter
        fields = "__all__"


class VariantComCSSerializer(serializers.ModelSerializer):
    class Meta:
        model = mst_com_cs_tbl
        fields = ["id", "ip_address", "device_name", "port"]


class BodyShopRecordSerializer(serializers.ModelSerializer):
    vin_image_base64 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = bodyshop_tbl
        fields = [
            "vin",
            "vin_ocr_result",
            "vin_status",
            "log_date",
            "operator",
            "qr_code",
            "vin_image",
            "vin_image_base64",
        ]
        read_only_fields = ["vin_image"]

    def create(self, validated_data):
        vin_image_data = validated_data.pop("vin_image_base64", None)
        instance = bodyshop_tbl(**validated_data)
        import base64
        import uuid

        from django.core.files.base import ContentFile

        if vin_image_data:
            # Generate filename
            filename = (
                f"{uuid.uuid4()}_BodyShop_{instance.qr_code}_{instance.vin_status}.jpg"
            )
            image_data = base64.b64decode(vin_image_data)
            instance.vin_image.save(filename, ContentFile(image_data), save=False)

        instance.save()
        return instance


class AnswerItemSerializer(serializers.Serializer):
    qr_code = serializers.CharField(allow_blank=True, required=False)
    vin = serializers.CharField(allow_blank=True, required=False)
    model_code = serializers.CharField()
    part_no = serializers.IntegerField(allow_null=True, required=False)
    part_name = serializers.CharField()
    answer = serializers.CharField()
    checkpoint = serializers.CharField(allow_blank=True, required=False)
    location = serializers.CharField(allow_blank=True, required=False)
    severity = serializers.CharField(allow_blank=True, required=False)
    attribute = serializers.CharField(allow_blank=True, required=False)
    highlight = serializers.CharField(allow_blank=True, required=False)
    concern = serializers.CharField(allow_blank=True, required=False)
    ocr_operation = serializers.CharField(allow_blank=True, required=False)
    actual_text = serializers.CharField(allow_blank=True, required=False)
    ocr_text = serializers.CharField(allow_blank=True, required=False)
    remark_image = serializers.CharField(allow_blank=True, required=False)
    vehicle_platform = serializers.CharField()
    emp_token = serializers.CharField()
    operator = serializers.CharField()
    part_time = serializers.CharField(allow_blank=True, required=False)
    image_path = serializers.CharField(allow_blank=True, required=False)
    qc_no = serializers.IntegerField()
    shift_name = serializers.CharField(allow_blank=True, required=False)
    image_processing_type = serializers.IntegerField(required=False)
    log_date = serializers.DateTimeField()


class VinDataSerializer(serializers.Serializer):
    qr_code = serializers.CharField()
    model_code = serializers.CharField()
    answer_status = serializers.CharField()
    shift_name = serializers.CharField()
    vehicle_platform = serializers.CharField()
    emp_token = serializers.CharField()
    operator = serializers.CharField()
    location = serializers.CharField()
    qc_no = serializers.CharField()
    log_date = serializers.DateTimeField()


class AnswerVinSerializer(serializers.Serializer):
    answers = AnswerItemSerializer(many=True)
    vin = VinDataSerializer(required=False)
