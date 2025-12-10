from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now


class Custom_user(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    log_date = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    team = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_custom_users')

    def __str__(self):
        return self.user.username

class CustomUser(User):
    class Meta:
        proxy = True
        app_label = "vms_webapp"
    # username = models.CharField(max_length=100)
    # password = models.CharField(max_length=100)
    # log_date = models.DateTimeField(auto_now=True)
    # user_level=models.ForeignKey("user_level_tbl", on_delete=models.CASCADE)

    def __str__(self):
        return self.username
# class model_code_tbl(models.Model):
#     model_code = models.CharField(max_length=16)
#     model_description = models.CharField(max_length=255)
#     platform = models.ForeignKey("platform", on_delete=models.CASCADE)
#     log_date = models.DateTimeField(auto_now=True)


class user_level_tbl(models.Model):
    user = models.CharField(max_length=255, null=True)
    def __str__(self):
        return self.user

# class user_tbl(models.Model):
#     user_name = models.CharField(max_length=255)
#     user = models.OneToOneField(User, on_delete=models.CASCADE)  # LINK to auth_user!
#     token = models.IntegerField()
#     user_level = models.ForeignKey(user_level_tbl, on_delete=models.SET_NULL, null=True)
#     created_by = models.ForeignKey(User, related_name='created_users', null=True, blank=True, on_delete=models.SET_NULL)
#     log_date = models.DateTimeField(auto_now=True)


class user_tbl(models.Model):
    user_name = models.CharField(max_length=255, unique=True)
    token = models.IntegerField(unique=True)
    user_level = models.CharField(max_length=255, null=True)
    log_date = models.DateTimeField(auto_now=True)


class platform(models.Model):
    platform = models.CharField(max_length=255)
    model_code_length = models.IntegerField(default=16, null=True, blank=True)
    log_date = models.DateTimeField(auto_now=True)


class part_tbl(models.Model):
    part_no = models.IntegerField()
    part_name = models.CharField(max_length=255)
    platform = models.ForeignKey("platform", on_delete=models.CASCADE, null=True, blank=True)
    image_path = models.ImageField(
        upload_to="image_path/image_path/part_images/", null=True, blank=True, max_length=255
    )
    severity = models.CharField(max_length=255, null=True, blank=True)
    attribute = models.CharField(max_length=255, null=True, blank=True)
    highlight = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    ocr_operation = models.CharField(
        max_length=255, default=1
    )  # Define ocr_operation field
    image_processing_type = models.ForeignKey(
        "Image_Processing", on_delete=models.CASCADE, null=True
    )
    log_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        # return super().__str__(), f"{self.part_no} - {self.part_name}"
        return f"{self.part_no} - {self.part_name}"
    
    class Meta:
        # Ensure part_name is unique per platform (platform-wise uniqueness)
        constraints = [
            models.UniqueConstraint(fields=['platform', 'part_name'], name='unique_part_name_per_platform')
        ]

class checkpoint_tbl(models.Model):
    part = models.ForeignKey(part_tbl, on_delete=models.CASCADE, null=True)
    checkpoint = models.CharField(max_length=255)
    platform = models.ForeignKey("Platform", on_delete=models.CASCADE, null=True, blank=True)
    log_date = models.DateTimeField(auto_now=True)



class model_checkpoint_tbl(models.Model):
    part = models.ForeignKey('part_tbl', on_delete=models.CASCADE, null=True)
    model = models.ForeignKey('model_code_tbl', on_delete=models.CASCADE, null=True)
    checkpoint = models.TextField()
    image_path = models.ImageField(
        upload_to="image_path/image_path/part_images/", null=True, blank=True, max_length=255
    )
    platform = models.ForeignKey('Platform', on_delete=models.CASCADE, null=True, blank=True)
    image_processing_type = models.ForeignKey("Image_Processing", on_delete=models.CASCADE, null=True)
    log_date = models.DateTimeField(auto_now=True)


class severity_tbl(models.Model):
    severity = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class location_tbl(models.Model):
    location = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class operation_tbl(models.Model):
    ocr_operation = models.CharField(max_length=255, null=True)
    log_date = models.DateTimeField(auto_now=True)


class attribute_tbl(models.Model):
    attribute = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class highlight_tbl(models.Model):
    highlight = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class concern_tbl(models.Model):
    concern = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class answer_tbl(models.Model):
    qr_code = models.CharField(max_length=255, null=True)
    model_code = models.CharField(max_length=255)
    qc_no = models.IntegerField()
    part_no = models.IntegerField(null=True)
    part_name = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    checkpoint = models.CharField(max_length=255, null=True, blank=True)
    severity = models.CharField(max_length=255, null=True)
    highlight = models.CharField(max_length=255, null=True)
    attribute = models.CharField(max_length=255, null=True)
    location = models.CharField(max_length=255, null=True)
    concern = models.CharField(max_length=255, null=True, blank=True)
    ocr_operation = models.CharField(max_length=255, null=True)
    remark_image = models.CharField(max_length=255)
    vehicle_platform = models.CharField(max_length=255)
    emp_token = models.CharField(max_length=255)
    operator = models.CharField(max_length=255)
    part_time = models.CharField(max_length=255, null=True)
    image_path = models.CharField(max_length=255, null=True)
    vin = models.CharField(max_length=255, null=True)
    actual_text = models.CharField(max_length=255, null=True, blank=True)
    ocr_text = models.CharField(max_length=255, null=True, blank=True)
    shift_name = models.CharField(max_length=255, null=True, blank=True)
    image_processing_type = models.IntegerField(null=True, blank=True)
    actual_text_new = models.CharField(max_length=255, null=True, blank=True)
    log_date = models.DateTimeField()


class battery_tbl(models.Model):
    main_qr = models.CharField(max_length=255)
    battery_qr = models.CharField(max_length=255)
    validity = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class mst_settableFields_tbl(models.Model):
    purging_limit = models.BigIntegerField()
    rotation_degree = models.IntegerField()
    capture_time = models.IntegerField()
    buzzer_ok_time = models.BigIntegerField()
    buzzer_nok_time = models.IntegerField()
    result_refresh_time = models.IntegerField()
    is_nok_image_capture_enable = models.BooleanField(null=True)
    is_iot_hooter_auto = models.BooleanField(null=True)
    is_body_shop_enable = models.BooleanField(null=True)
    is_ok_concern_enable = models.BooleanField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class boundingbox_tbl(models.Model):
    left_value = models.IntegerField()
    right_value = models.IntegerField()
    top_value = models.IntegerField()
    bottom_value = models.IntegerField()
    box_type = models.CharField(max_length=255)
    position = models.IntegerField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class boundingbox_cd_tbl(models.Model):
    modelid = models.CharField(null=True, blank=True, max_length=50)
    position = models.IntegerField(null=True)
    left = models.IntegerField()
    right = models.IntegerField()
    top = models.IntegerField()
    bottom = models.IntegerField()
    c1_r_from = models.IntegerField(default=0)
    c1_g_from = models.IntegerField(default=0)
    c1_b_from = models.IntegerField(default=0)
    c1_r_to = models.IntegerField(default=0)
    c1_g_to = models.IntegerField(default=0)
    c1_b_to = models.IntegerField(default=0)
    c2_r_from = models.IntegerField(default=0)
    c2_g_from = models.IntegerField(default=0)
    c2_b_from = models.IntegerField(default=0)
    c2_r_to = models.IntegerField(default=0)
    c2_g_to = models.IntegerField(default=0)
    c2_b_to = models.IntegerField(default=0)
    c1IgnorePixelCount = models.IntegerField(default=0)
    c2IgnorePixelCount = models.IntegerField(default=0)
    pixel_range = models.IntegerField(default=0)
    greater_less_than = models.CharField(max_length=50)
    ok_nok = models.CharField(max_length=10)
    log_date = models.DateTimeField(auto_now=True)


class mst_com_cs_tbl(models.Model):
    ip_address = models.CharField(max_length=20)
    device_name = models.CharField(max_length=20)
    port = models.IntegerField()
    sync_status = models.BooleanField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class mst_com_ser_tbl(models.Model):
    ip_address = models.CharField(max_length=20)
    retry_time = models.IntegerField(1000)
    sync_status = models.BooleanField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class characters_tbl(models.Model):
    is_alphabet = models.BooleanField()
    is_number = models.BooleanField()
    character_type = models.CharField(max_length=50)
    log_date = models.DateTimeField(auto_now=True)


class delete_tbl(models.Model):
    table_name = models.CharField(max_length=255)
    data_id = models.IntegerField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class Shift(models.Model):
    Shift_name = models.CharField(max_length=255)
    Shift_From = models.TimeField(max_length=8)
    Shift_To = models.TimeField()
    log_date = models.DateTimeField(auto_now=True)


class PurgingData(models.Model):
    purging_limit = models.IntegerField()
    log_date = models.DateTimeField(auto_now=True)


class vin_report_tbl(models.Model):
    qr_code = models.CharField(max_length=255)
    model_code = models.CharField(max_length=255)
    answer_status = models.CharField(max_length=255)
    shift_name = models.CharField(max_length=255)
    vehicle_platform = models.CharField(max_length=255)
    emp_token = models.CharField(max_length=255)
    operator = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    qc_no = models.CharField(max_length=255)
    log_date = models.DateTimeField()


class bodyshop_tbl(models.Model):
    vin = models.CharField(max_length=255)
    vin_ocr_result = models.CharField(max_length=255)
    vin_status = models.CharField(max_length=255)
    vin_image = models.CharField(max_length=255)
    operator = models.CharField(max_length=255)
    qr_code = models.CharField(max_length=255)
    log_date = models.DateTimeField(auto_now=True)


class Show_report(models.Model):
    image_url = models.CharField(max_length=255, null=True)
    Date_Field = models.DateField()
    shift = models.ForeignKey("Shift", on_delete=models.SET_NULL, null=True)
    log_date = models.DateTimeField(auto_now=True)


class Image_Processing(models.Model):
    image_process = models.CharField(max_length=255)
    no_of_char = models.IntegerField(null=True)
    position_of_text = models.IntegerField()
    variable = models.CharField(max_length=255)
    description_of_text = models.CharField(max_length=255)
    is_qr_applicable = models.IntegerField(default=1)
    zoom=models.FloatField(null=True)
    log_date = models.DateTimeField(auto_now=True)


class color_code_tbl(models.Model):
    color_code = models.CharField(max_length=255)
    color_name = models.CharField(max_length=255)
    r_from = models.IntegerField(default=0)
    g_from = models.IntegerField(default=0)
    b_from = models.IntegerField(default=0)
    r_to = models.IntegerField(default=0)
    g_to = models.IntegerField(default=0)
    b_to = models.IntegerField(default=0)
    log_date = models.DateTimeField(auto_now=True)


class ActionLog(models.Model):
    ACTION_CHOICES = [
        ("ADD", "Add"),
        ("EDIT", "Edit"),
        ("DELETE", "Delete"),
    ]
    table_name = models.CharField(max_length=255)
    data_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=now)
    details = models.TextField(null=True, blank=True)
    description = models.TextField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    log_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.action} on {self.table_name} (ID: {self.data_id}) at {self.timestamp}"


class VariantFuelCharacter(models.Model):

    fuel_character = models.CharField(max_length=100)
    fuel_type = models.CharField(max_length=50)
    log_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fuel_character} - {self.fuel_type}"


class VariantShowReport(models.Model):
    variant_code = models.CharField(max_length=100)
    model_code = models.CharField(max_length=100)
    platform = models.CharField(max_length=100)
    fuel_type = models.CharField(max_length=50)
    transmission_type = models.CharField(max_length=50)
    show_date = models.DateField()
    location = models.CharField(max_length=255)
    no_of_units_displayed = models.IntegerField()
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.variant_code} shown on {self.show_date}"


class VariantImageProcessing(models.Model):
    variant_code = models.CharField(max_length=100)
    image = models.ImageField(upload_to="variant_images/")
    processed_image = models.ImageField(
        upload_to="processed_variant_images/", null=True, blank=True
    )
    processing_status = models.CharField(
        max_length=50,
        choices=[
            ("Pending", "Pending"),
            ("In Progress", "In Progress"),
            ("Completed", "Completed"),
            ("Failed", "Failed"),
        ],
        default="Pending",
    )
    processing_notes = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    log_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.variant_code} - {self.processing_status}"


class Polygon(models.Model):
    polygon = models.TextField()
    model = models.CharField(max_length=255, default="")
    sync_status = models.BooleanField()


class severity_count_tbl(models.Model):
    severity = models.CharField(max_length=255)
    total_count = models.IntegerField()
    severity_ok_count = models.IntegerField()
    severity_nok_count = models.IntegerField()
    qc= models.IntegerField(null=True)
    data_date = models.DateField(null=True)  # The date this count represents
    log_date = models.DateTimeField(auto_now=True)

class higlight_count_tbl(models.Model):
    highlight = models.CharField(max_length=255)
    total_count = models.IntegerField()
    highlight_ok_count = models.IntegerField()
    highlight_nok_count = models.IntegerField()
    qc= models.IntegerField(null=True)
    data_date = models.DateField(null=True)  # The date this count represents
    log_date = models.DateTimeField(auto_now=True)

class attribute_count_tbl(models.Model):
    attribute = models.CharField(max_length=255)
    total_count = models.IntegerField()
    attribute_ok_count = models.IntegerField()
    attribute_nok_count = models.IntegerField()
    qc= models.IntegerField(null=True)
    data_date = models.DateField(null=True)  # The date this count represents
    log_date = models.DateTimeField(auto_now=True)

class RatioMaster(models.Model):
    ratio = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.ratio


class BurdenMaster(models.Model):
    burden = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.burden


class FerruleDirectionMaster(models.Model):
    direction = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.direction


class LabelTypeMaster(models.Model):
    label_type = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.label_type


class FerruleNumberMaster(models.Model):
    number = models.IntegerField(unique=True)

    def __str__(self):
        return str(self.number)

class model_code_tbl(models.Model):
    model_code = models.CharField(max_length=255)
    model_description = models.CharField(max_length=255)
    platform = models.ForeignKey("platform", on_delete=models.CASCADE)
    ratio = models.CharField(max_length=50)
    burden = models.CharField(max_length=50)
    label_type = models.CharField(max_length=255)
    ferrule_direction = models.CharField(max_length=255)
    no_of_ferrules = models.IntegerField()
    log_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.model_code} - {self.model_description}"

