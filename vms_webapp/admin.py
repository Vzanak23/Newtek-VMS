from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Custom_user
from import_export.admin import ImportExportModelAdmin
from .models import *
from import_export import resources


# Example base resource for reuse
class BaseResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True


# Example base admin
class BaseAdmin(ImportExportModelAdmin):
    list_per_page = 50
    # ordering = ['-log_date']
    # readonly_fields = ['log_date']
    # date_hierarchy = 'log_date'


# ------- Register each model with search/filter/custom display -------


# ✅ Inline profile for User admin
class CustomUserInline(admin.StackedInline):
    model = Custom_user
    can_delete = False
    verbose_name_plural = 'Profile'

    fk_name = 'user'  # Link to User model

# ✅ Extend built-in User admin to show Custom_user inline
class UserAdmin(BaseUserAdmin):
    inlines = (CustomUserInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_team', 'get_is_admin', 'get_created_by')
    search_fields = ('username', 'email', 'custom_user__team')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    def get_team(self, obj):
        return obj.custom_user.team if hasattr(obj, 'custom_user') else '-'
    get_team.short_description = 'Team'

    def get_is_admin(self, obj):
        return obj.custom_user.is_admin if hasattr(obj, 'custom_user') else False
    get_is_admin.short_description = 'Is Admin'

    def get_created_by(self, obj):
        return obj.custom_user.created_by if hasattr(obj, 'custom_user') else '-'
    get_created_by.short_description = 'Created By'

# ✅ Unregister default User admin & re-register with our custom version
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# ✅  register Custom_user directly → makes it easy to bulk manage
@admin.register(Custom_user)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'is_admin', 'created_by', 'log_date')
    search_fields = ['user__username', 'team']
    list_filter = ['log_date', 'is_admin']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(model_code_tbl)
class ModelCodeAdmin(admin.ModelAdmin):
    list_display = ['model_code', 'ratio', 'burden', 'ferrule_direction', 'no_of_ferrules', 'log_date']
    list_filter = ['ratio', 'burden', 'ferrule_direction', 'no_of_ferrules']
    search_fields = ['model_code']


@admin.register(user_tbl)
class UserTblAdmin(BaseAdmin):
    list_display = ['user_name', 'token', 'user_level', 'log_date']
    search_fields = ['user_name', 'token', 'user_level']
    list_filter = ['user_level', 'log_date']


@admin.register(user_level_tbl)
class UserLevelTblAdmin(BaseAdmin):
    list_display = ['user']
    search_fields = ['user']


@admin.register(platform)
class PlatformAdmin(BaseAdmin):
    list_display = ['platform', 'model_code_length', 'log_date']
    search_fields = ['platform']
    list_filter = ['log_date']


@admin.register(part_tbl)
class PartTblAdmin(BaseAdmin):
    list_display = ['part_no', 'part_name', 'severity', 'attribute', 'highlight', 'location', 'ocr_operation', 'log_date']
    search_fields = ['part_no', 'part_name', 'severity', 'attribute', 'highlight', 'location']
    list_filter = ['severity', 'attribute', 'highlight', 'location', 'log_date']


@admin.register(checkpoint_tbl)
class CheckpointTblAdmin(BaseAdmin):
    list_display = ['part', 'checkpoint', 'log_date']
    search_fields = ['checkpoint']
    list_filter = ['log_date']


@admin.register(model_checkpoint_tbl)
class ModelCheckpointTblAdmin(BaseAdmin):
    list_display = ['model', 'part',  'log_date']
    search_fields = ['model__model_code', 'part__part_name']
    list_filter = [ 'log_date']


@admin.register(severity_tbl)
class SeverityTblAdmin(BaseAdmin):
    list_display = ['severity', 'log_date']
    search_fields = ['severity']
    list_filter = ['log_date']


@admin.register(location_tbl)
class LocationTblAdmin(BaseAdmin):
    list_display = ['location', 'log_date']
    search_fields = ['location']
    list_filter = ['log_date']


@admin.register(operation_tbl)
class OperationTblAdmin(BaseAdmin):
    list_display = ['ocr_operation', 'log_date']
    search_fields = ['ocr_operation']
    list_filter = ['log_date']


@admin.register(attribute_tbl)
class AttributeTblAdmin(BaseAdmin):
    list_display = ['attribute', 'log_date']
    search_fields = ['attribute']
    list_filter = ['log_date']


@admin.register(highlight_tbl)
class HighlightTblAdmin(BaseAdmin):
    list_display = ['highlight', 'log_date']
    search_fields = ['highlight']
    list_filter = ['log_date']


@admin.register(concern_tbl)
class ConcernTblAdmin(BaseAdmin):
    list_display = ['concern', 'log_date']
    search_fields = ['concern']
    list_filter = ['log_date']


@admin.register(answer_tbl)
class AnswerTblAdmin(BaseAdmin):
    list_display = ['qr_code', 'model_code', 'qc_no', 'part_no', 'operator', 'log_date']
    search_fields = ['qr_code', 'model_code', 'part_name', 'operator']
    list_filter = ['shift_name', 'vehicle_platform', 'log_date']


@admin.register(battery_tbl)
class BatteryTblAdmin(BaseAdmin):
    list_display = ['main_qr', 'battery_qr', 'validity', 'status', 'log_date']
    search_fields = ['main_qr', 'battery_qr']
    list_filter = ['status', 'log_date']


@admin.register(mst_settableFields_tbl)
class MstSettableFieldsTblAdmin(BaseAdmin):
    list_display = ['purging_limit', 'rotation_degree', 'capture_time', 'buzzer_ok_time', 'buzzer_nok_time', 'result_refresh_time', 'log_date']
    list_filter = ['log_date']


@admin.register(boundingbox_tbl)
class BoundingboxTblAdmin(BaseAdmin):
    list_display = ['left_value', 'right_value', 'top_value', 'bottom_value', 'box_type', 'position', 'log_date']
    list_filter = ['box_type', 'log_date']


@admin.register(boundingbox_cd_tbl)
class BoundingboxCdTblAdmin(BaseAdmin):
    list_display = ['modelid', 'position', 'greater_less_than', 'ok_nok', 'log_date']
    list_filter = ['greater_less_than', 'ok_nok', 'log_date']


@admin.register(mst_com_cs_tbl)
class MstComCsTblAdmin(BaseAdmin):
    list_display = ['ip_address', 'device_name', 'port', 'sync_status', 'log_date']
    search_fields = ['ip_address', 'device_name']
    list_filter = ['sync_status', 'log_date']


@admin.register(mst_com_ser_tbl)
class MstComSerTblAdmin(BaseAdmin):
    list_display = ['ip_address', 'retry_time', 'sync_status', 'log_date']
    search_fields = ['ip_address']
    list_filter = ['sync_status', 'log_date']


@admin.register(characters_tbl)
class CharactersTblAdmin(BaseAdmin):
    list_display = ['is_alphabet', 'is_number', 'character_type', 'log_date']
    search_fields = ['character_type']
    list_filter = ['is_alphabet', 'is_number', 'log_date']


@admin.register(delete_tbl)
class DeleteTblAdmin(BaseAdmin):
    list_display = ['table_name', 'data_id', 'log_date']
    search_fields = ['table_name']
    list_filter = ['log_date']


@admin.register(Shift)
class ShiftAdmin(BaseAdmin):
    list_display = ['Shift_name', 'Shift_From', 'Shift_To', 'log_date']
    search_fields = ['Shift_name']
    list_filter = ['log_date']


@admin.register(PurgingData)
class PurgingDataAdmin(BaseAdmin):
    list_display = ['purging_limit', 'log_date']
    list_filter = ['log_date']


@admin.register(vin_report_tbl)
class VinReportTblAdmin(BaseAdmin):
    list_display = ['qr_code', 'model_code', 'answer_status', 'shift_name', 'vehicle_platform', 'operator', 'log_date']
    search_fields = ['qr_code', 'model_code', 'operator']
    list_filter = ['shift_name', 'vehicle_platform', 'log_date']


@admin.register(bodyshop_tbl)
class BodyshopTblAdmin(BaseAdmin):
    list_display = ['vin', 'vin_ocr_result', 'vin_status', 'operator', 'qr_code', 'log_date']
    search_fields = ['vin', 'vin_ocr_result', 'operator', 'qr_code']
    list_filter = ['vin_status', 'log_date']


@admin.register(Show_report)
class ShowReportAdmin(BaseAdmin):
    list_display = ['image_url', 'Date_Field', 'shift', 'log_date']
    search_fields = ['image_url']
    list_filter = ['shift', 'Date_Field', 'log_date']


@admin.register(Image_Processing)
class ImageProcessingAdmin(BaseAdmin):
    list_display = ['image_process', 'no_of_char', 'position_of_text', 'variable', 'description_of_text', 'log_date']
    search_fields = ['image_pr0ocess', 'variable']
    list_filter = ['log_date']


@admin.register(color_code_tbl)
class ColorCodeTblAdmin(BaseAdmin):
    list_display = ['color_code', 'color_name', 'log_date']
    search_fields = ['color_code', 'color_name']
    list_filter = ['log_date']


@admin.register(ActionLog)
class ActionLogAdmin(BaseAdmin):
    list_display = ['table_name', 'data_id', 'action', 'timestamp', 'user', 'log_date']
    search_fields = ['table_name', 'action', 'user__username']
    list_filter = ['action', 'log_date']


@admin.register(VariantFuelCharacter)
class VariantFuelCharacterAdmin(BaseAdmin):
    list_display = ['fuel_character', 'fuel_type', 'log_date']
    search_fields = ['fuel_character', 'fuel_type']
    list_filter = ['log_date']


# @admin.register(VariantShowReport)
# class VariantShowReportAdmin(BaseAdmin):
#     list_display = ['variant_code', 'model_code', 'platform', 'fuel_type', 'transmission_type', 'show_date', 'log_date']
#     search_fields = ['variant_code', 'model_code', 'platform']
#     list_filter = ['fuel_type', 'transmission_type', 'show_date', 'log_date']


@admin.register(VariantImageProcessing)
class VariantImageProcessingAdmin(BaseAdmin):
    list_display = ['variant_code', 'processing_status', 'uploaded_at', 'processed_at', 'log_date']
    search_fields = ['variant_code']
    list_filter = ['processing_status', 'log_date']


@admin.register(Polygon)
class PolygonAdmin(BaseAdmin):
    list_display = ['model', 'sync_status']
    search_fields = ['model']
    list_filter = ['sync_status']


class delete_tblAdmin(admin.ModelAdmin):
    actions = ['purge_records']

    def purge_records(self, request, queryset):
        # Define your purging limit (e.g., 100 records)
        purging_limit = 5
        # Get the IDs of the records to be deleted
        record_ids_to_delete = list(queryset.values_list('id', flat=True)[:purging_limit])
        # Delete records up to the purging limit
        deleted_count = delete_tbl.objects.filter(id__in=record_ids_to_delete).delete()[0]
        self.message_user(request, f"{deleted_count} records purged successfully.")

    purge_records.short_description = "Purge selected records (up to a limit)"

# Register your model with the custom admin class
# admin.site.register(delete_tbl, delete_tblAdmin)